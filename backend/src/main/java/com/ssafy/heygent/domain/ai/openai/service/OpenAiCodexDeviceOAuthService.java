package com.ssafy.heygent.domain.ai.openai.service;

import java.io.BufferedReader;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.ArrayList;
import java.util.Base64;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.ssafy.heygent.domain.ai.dto.response.OpenAiCodexDeviceOAuthStartResponse;
import com.ssafy.heygent.domain.ai.dto.response.OpenAiCodexDeviceOAuthStatusResponse;
import com.ssafy.heygent.domain.ai.openai.config.OpenAiProperties;
import com.ssafy.heygent.domain.ai.openai.entity.OpenAiProviderConnection;
import com.ssafy.heygent.domain.ai.openai.model.OpenAiProviderName;
import com.ssafy.heygent.domain.ai.openai.repository.OpenAiProviderConnectionRepository;
import com.ssafy.heygent.domain.ai.openai.security.OpenAiCredentialCipher;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

import jakarta.annotation.PreDestroy;
import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
public class OpenAiCodexDeviceOAuthService {

    private static final String CODEX_SCOPE = "codex";
    private static final String TOKEN_TYPE = "Bearer";
    private static final String DEVICE_STATE_PREFIX = "codex_device_";

    private final OpenAiProperties properties;
    private final OpenAiProviderConnectionRepository openAiProviderConnectionRepository;
    private final OpenAiCredentialCipher credentialCipher;
    private final ObjectMapper objectMapper;
    private final Map<String, PendingCodexDeviceAuth> pendingAuths = new ConcurrentHashMap<>();
    private final ExecutorService streamReaderExecutor = Executors.newCachedThreadPool();

    @Transactional
    public OpenAiCodexDeviceOAuthStartResponse start(Long userId) {
        validateConfigured();
        cleanupUserPendingAuths(userId);

        String state = DEVICE_STATE_PREFIX + UUID.randomUUID();
        LocalDateTime expiresAt = LocalDateTime.now()
            .plusSeconds(properties.getCodexDeviceOAuth().getAuthTimeoutSeconds());
        Path codexHome = codexHome(userId, state);

        try {
            Files.createDirectories(codexHome);
            Process process = processBuilder(codexHome).start();
            OutputCollector outputCollector = new OutputCollector();
            streamReaderExecutor.submit(() -> readStream(process, outputCollector, process.inputReader()));
            streamReaderExecutor.submit(() -> readStream(process, outputCollector, process.errorReader()));

            CodexDeviceAuthOutputParser.ParsedDeviceAuthOutput parsedOutput =
                waitForDeviceAuthOutput(process, outputCollector);
            if (!parsedOutput.isComplete()) {
                destroy(process);
                deleteCodexHome(codexHome);
                throw new CustomException(ErrorCode.OPENAI_PROVIDER_NOT_CONFIGURED);
            }

            pendingAuths.put(state, new PendingCodexDeviceAuth(
                userId,
                state,
                codexHome,
                process,
                expiresAt,
                parsedOutput.verificationUri(),
                parsedOutput.userCode()
            ));

            return OpenAiCodexDeviceOAuthStartResponse.builder()
                .providerName(OpenAiProviderName.OPENAI_CODEX_OAUTH.getValue())
                .state(state)
                .status("authorization_required")
                .verificationUri(parsedOutput.verificationUri())
                .userCode(parsedOutput.userCode())
                .expiresAt(expiresAt)
                .message("OpenAI 인증 페이지에서 코드를 입력하세요.")
                .build();
        } catch (CustomException exception) {
            throw exception;
        } catch (Exception exception) {
            deleteCodexHome(codexHome);
            throw new CustomException(ErrorCode.OPENAI_PROVIDER_NOT_CONFIGURED);
        }
    }

    @Transactional
    public OpenAiCodexDeviceOAuthStatusResponse status(Long userId, String state) {
        PendingCodexDeviceAuth pending = pendingAuth(userId, state);
        if (LocalDateTime.now().isAfter(pending.expiresAt())) {
            removePending(pending);
            return response(pending, false, false, "expired", null, null, "인증 시간이 만료되었습니다.");
        }

        Optional<Path> authJsonPath = authJsonPath(pending.codexHome());
        if (authJsonPath.isEmpty()) {
            if (!pending.process().isAlive()) {
                removePending(pending);
                return response(pending, false, false, "failed", null, null, "Codex 인증 프로세스가 종료되었습니다.");
            }
            return response(pending, false, false, "pending", null, null, "OpenAI 인증 완료를 기다리는 중입니다.");
        }

        CodexDeviceCredential credential = readCredential(authJsonPath.get());
        OpenAiProviderConnection connection = upsertConnection(userId, credential);
        removePending(pending);

        return response(
            pending,
            true,
            true,
            "connected",
            valueOrNull(connection.getMetadata(), "accountId"),
            connection.getExpiresAt(),
            "Codex OAuth 연결이 완료되었습니다."
        );
    }

    private PendingCodexDeviceAuth pendingAuth(Long userId, String state) {
        if (!StringUtils.hasText(state)) {
            throw new CustomException(ErrorCode.OPENAI_OAUTH_STATE_INVALID);
        }

        PendingCodexDeviceAuth pending = pendingAuths.get(state);
        if (pending == null || !pending.userId().equals(userId)) {
            throw new CustomException(ErrorCode.OPENAI_OAUTH_STATE_INVALID);
        }
        return pending;
    }

    private OpenAiProviderConnection upsertConnection(Long userId, CodexDeviceCredential credential) {
        OpenAiProviderConnection connection = openAiProviderConnectionRepository
            .findByUserIdAndProviderName(userId, OpenAiProviderName.OPENAI_CODEX_OAUTH.getValue())
            .orElseGet(() -> OpenAiProviderConnection.builder()
                .userId(userId)
                .providerName(OpenAiProviderName.OPENAI_CODEX_OAUTH.getValue())
                .build());

        connection.updateToken(
            TOKEN_TYPE,
            credentialCipher.encrypt(credential.accessToken()),
            credentialCipher.encrypt(credential.refreshToken()),
            CODEX_SCOPE,
            credential.expiresAt(),
            Map.of(
                "accountId", valueOrEmpty(credential.accountId()),
                "credentialFormat", "device_oauth",
                "hasRefreshToken", StringUtils.hasText(credential.refreshToken())
            )
        );
        return openAiProviderConnectionRepository.save(connection);
    }

    private CodexDeviceCredential readCredential(Path authJsonPath) {
        try {
            JsonNode root = objectMapper.readTree(Files.readString(authJsonPath, StandardCharsets.UTF_8));
            JsonNode tokenNode = root.has("tokens") ? root.get("tokens") : root;
            String accessToken = findText(tokenNode, "access_token", "accessToken", "access");
            if (!StringUtils.hasText(accessToken)) {
                throw new CustomException(ErrorCode.OPENAI_OAUTH_TOKEN_EXCHANGE_FAILED);
            }

            return new CodexDeviceCredential(
                accessToken,
                findText(tokenNode, "refresh_token", "refreshToken", "refresh"),
                expiresAt(accessToken, root, tokenNode),
                firstText(
                    findText(tokenNode, "account_id", "accountId"),
                    accountId(findText(tokenNode, "id_token", "idToken")),
                    accountId(accessToken)
                )
            );
        } catch (CustomException exception) {
            throw exception;
        } catch (Exception exception) {
            throw new CustomException(ErrorCode.OPENAI_OAUTH_TOKEN_EXCHANGE_FAILED);
        }
    }

    private LocalDateTime expiresAt(String accessToken, JsonNode root, JsonNode tokenNode) {
        LocalDateTime explicitExpiresAt = firstDateTime(
            findText(tokenNode, "expires_at", "expiresAt"),
            findText(root, "expires_at", "expiresAt")
        );
        if (explicitExpiresAt != null) {
            return explicitExpiresAt;
        }

        JsonNode payload = tokenPayload(accessToken);
        if (payload == null || !payload.has("exp")) {
            return null;
        }
        return LocalDateTime.ofInstant(
            Instant.ofEpochSecond(payload.get("exp").asLong()),
            ZoneId.systemDefault()
        );
    }

    private LocalDateTime firstDateTime(String... values) {
        for (String value : values) {
            if (!StringUtils.hasText(value)) {
                continue;
            }
            try {
                return LocalDateTime.ofInstant(Instant.parse(value), ZoneId.systemDefault());
            } catch (Exception ignored) {
                try {
                    return LocalDateTime.parse(value);
                } catch (Exception ignoredAgain) {
                    // Try the next candidate.
                }
            }
        }
        return null;
    }

    private String accountId(String token) {
        JsonNode payload = tokenPayload(token);
        if (payload == null) {
            return null;
        }
        JsonNode auth = payload.get("https://api.openai.com/auth");
        if (auth != null && auth.has("chatgpt_account_id")) {
            return auth.get("chatgpt_account_id").asText();
        }
        if (payload.has("account_id")) {
            return payload.get("account_id").asText();
        }
        return null;
    }

    private JsonNode tokenPayload(String token) {
        if (!StringUtils.hasText(token)) {
            return null;
        }
        String[] parts = token.split("\\.");
        if (parts.length < 2) {
            return null;
        }
        try {
            String payload = new String(Base64.getUrlDecoder().decode(padBase64(parts[1])), StandardCharsets.UTF_8);
            return objectMapper.readTree(payload);
        } catch (Exception exception) {
            return null;
        }
    }

    private String padBase64(String value) {
        int remainder = value.length() % 4;
        if (remainder == 0) {
            return value;
        }
        return value + "=".repeat(4 - remainder);
    }

    private String findText(JsonNode node, String... fieldNames) {
        if (node == null || node.isNull()) {
            return null;
        }
        for (String fieldName : fieldNames) {
            JsonNode value = node.get(fieldName);
            if (value != null && value.isTextual() && StringUtils.hasText(value.asText())) {
                return value.asText();
            }
        }
        return null;
    }

    private String firstText(String... values) {
        for (String value : values) {
            if (StringUtils.hasText(value)) {
                return value;
            }
        }
        return null;
    }

    private ProcessBuilder processBuilder(Path codexHome) {
        List<String> command = new ArrayList<>();
        command.add(resolveCommand());
        command.add("login");
        command.add("--device-auth");

        ProcessBuilder processBuilder = new ProcessBuilder(command);
        processBuilder.environment().put("CODEX_HOME", codexHome.toString());
        processBuilder.environment().put("NO_COLOR", "1");
        return processBuilder;
    }

    private String resolveCommand() {
        String command = properties.getCodexDeviceOAuth().getCommand();
        if (!StringUtils.hasText(command)) {
            command = "codex";
        }
        if (isWindows() && !command.contains(".") && !command.contains("/") && !command.contains("\\")) {
            return command + ".cmd";
        }
        return command;
    }

    private boolean isWindows() {
        return System.getProperty("os.name", "").toLowerCase().contains("win");
    }

    private CodexDeviceAuthOutputParser.ParsedDeviceAuthOutput waitForDeviceAuthOutput(
        Process process,
        OutputCollector outputCollector
    ) throws InterruptedException {
        long deadlineNanos = System.nanoTime()
            + TimeUnit.SECONDS.toNanos(properties.getCodexDeviceOAuth().getStartTimeoutSeconds());

        CodexDeviceAuthOutputParser.ParsedDeviceAuthOutput parsedOutput =
            CodexDeviceAuthOutputParser.parse(outputCollector.output());
        while (!parsedOutput.isComplete()
            && process.isAlive()
            && System.nanoTime() < deadlineNanos) {
            outputCollector.await(500);
            parsedOutput = CodexDeviceAuthOutputParser.parse(outputCollector.output());
        }
        return parsedOutput;
    }

    private void readStream(Process process, OutputCollector outputCollector, BufferedReader reader) {
        try (reader) {
            String line;
            while ((line = reader.readLine()) != null) {
                outputCollector.append(line);
            }
        } catch (IOException exception) {
            if (process.isAlive()) {
                outputCollector.append(exception.getMessage());
            }
        }
    }

    private Path codexHome(Long userId, String state) {
        return workspaceRoot()
            .resolve("user-" + userId)
            .resolve(state)
            .toAbsolutePath()
            .normalize();
    }

    private Path workspaceRoot() {
        String configuredRoot = properties.getCodexDeviceOAuth().getWorkspaceRoot();
        if (StringUtils.hasText(configuredRoot)) {
            return Path.of(configuredRoot).toAbsolutePath().normalize();
        }
        return Path.of(System.getProperty("user.home"), ".heygent", "codex-device-oauth")
            .toAbsolutePath()
            .normalize();
    }

    private Optional<Path> authJsonPath(Path codexHome) {
        List<Path> candidates = List.of(
            codexHome.resolve("auth.json"),
            codexHome.resolve(".codex").resolve("auth.json")
        );
        return candidates.stream()
            .filter(Files::isRegularFile)
            .findFirst();
    }

    private void cleanupUserPendingAuths(Long userId) {
        pendingAuths.values().stream()
            .filter(pending -> pending.userId().equals(userId))
            .toList()
            .forEach(this::removePending);
    }

    private void removePending(PendingCodexDeviceAuth pending) {
        pendingAuths.remove(pending.state());
        destroy(pending.process());
        deleteCodexHome(pending.codexHome());
    }

    private void destroy(Process process) {
        if (process != null && process.isAlive()) {
            process.destroy();
            try {
                if (!process.waitFor(2, TimeUnit.SECONDS)) {
                    process.destroyForcibly();
                }
            } catch (InterruptedException exception) {
                Thread.currentThread().interrupt();
                process.destroyForcibly();
            }
        }
    }

    private void deleteCodexHome(Path codexHome) {
        Path root = workspaceRoot();
        Path target = codexHome.toAbsolutePath().normalize();
        if (!target.startsWith(root) || target.equals(root)) {
            return;
        }

        try (var paths = Files.walk(target)) {
            paths.sorted(Comparator.reverseOrder())
                .forEach(path -> {
                    try {
                        Files.deleteIfExists(path);
                    } catch (IOException ignored) {
                        // Best-effort cleanup for temporary device auth files.
                    }
                });
        } catch (IOException ignored) {
            // Best-effort cleanup for temporary device auth files.
        }
    }

    private OpenAiCodexDeviceOAuthStatusResponse response(
        PendingCodexDeviceAuth pending,
        boolean connected,
        boolean available,
        String status,
        String accountId,
        LocalDateTime expiresAt,
        String message
    ) {
        return OpenAiCodexDeviceOAuthStatusResponse.builder()
            .providerName(OpenAiProviderName.OPENAI_CODEX_OAUTH.getValue())
            .state(pending.state())
            .connected(connected)
            .available(available)
            .status(status)
            .accountId(accountId)
            .expiresAt(expiresAt)
            .message(message)
            .build();
    }

    private void validateConfigured() {
        if (!properties.hasCredentialEncryptionKey()) {
            throw new CustomException(ErrorCode.OPENAI_PROVIDER_NOT_CONFIGURED);
        }
    }

    private String valueOrNull(Map<String, Object> metadata, String key) {
        if (metadata == null || metadata.get(key) == null) {
            return null;
        }
        return String.valueOf(metadata.get(key));
    }

    private String valueOrEmpty(String value) {
        return value == null ? "" : value;
    }

    @PreDestroy
    void shutdown() {
        pendingAuths.values().forEach(this::removePending);
        streamReaderExecutor.shutdownNow();
    }

    private record PendingCodexDeviceAuth(
        Long userId,
        String state,
        Path codexHome,
        Process process,
        LocalDateTime expiresAt,
        String verificationUri,
        String userCode
    ) {
    }

    private record CodexDeviceCredential(
        String accessToken,
        String refreshToken,
        LocalDateTime expiresAt,
        String accountId
    ) {
    }

    private static final class OutputCollector {

        private final StringBuilder output = new StringBuilder();
        private CountDownLatch latch = new CountDownLatch(1);

        synchronized void append(String line) {
            output.append(line).append('\n');
            latch.countDown();
            latch = new CountDownLatch(1);
        }

        synchronized String output() {
            return output.toString();
        }

        void await(long millis) throws InterruptedException {
            CountDownLatch currentLatch;
            synchronized (this) {
                currentLatch = latch;
            }
            currentLatch.await(millis, TimeUnit.MILLISECONDS);
        }
    }
}
