package com.ssafy.heygent.domain.ai.openai.config;

import java.util.ArrayList;
import java.util.List;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;

import lombok.Getter;
import lombok.Setter;

@Getter
@Setter
@Component
@ConfigurationProperties(prefix = "openai")
public class OpenAiProperties {

    private String apiKey = "";
    private String restApiBaseUrl = "https://api.openai.com/v1";
    private String usageApiBaseUrl = "https://api.openai.com/v1";
    private String defaultModel = "gpt-5.4";
    private List<String> allowedModels = new ArrayList<>(List.of("gpt-5.4", "gpt-5.4-mini"));
    private String embeddingModel = "text-embedding-3-small";
    private int timeoutSeconds = 60;
    private String credentialEncryptionKey = "";
    private OAuth oauth = new OAuth();
    private CodexOAuth codexOAuth = new CodexOAuth();
    private CodexDeviceOAuth codexDeviceOAuth = new CodexDeviceOAuth();

    public boolean hasApiKey() {
        return StringUtils.hasText(apiKey);
    }

    public List<String> normalizedAllowedModels() {
        return allowedModels.stream()
            .filter(StringUtils::hasText)
            .map(String::trim)
            .toList();
    }

    public boolean hasCredentialEncryptionKey() {
        return StringUtils.hasText(credentialEncryptionKey);
    }

    @Getter
    @Setter
    public static class OAuth {

        private String clientId = "";
        private String clientSecret = "";
        private String redirectUri = "http://localhost:8080/api/v1/ai/openai/oauth/callback";
        private String authorizeUrl = "https://auth.openai.com/oauth/authorize";
        private String tokenUrl = "https://auth.openai.com/oauth/token";
        private List<String> scopes = new ArrayList<>(List.of("openid", "profile", "email", "offline_access"));
    }

    @Getter
    @Setter
    public static class CodexOAuth {

        private String clientId = "app_EMoamEEZ73f0CkXaXp7hrann";
        private String redirectUri = "http://localhost:1455/auth/callback";
        private String authorizeUrl = "https://auth.openai.com/oauth/authorize";
        private String tokenUrl = "https://auth.openai.com/oauth/token";
        private List<String> scopes = new ArrayList<>(List.of("openid", "profile", "email", "offline_access"));
        private int refreshSkewSeconds = 300;
    }

    @Getter
    @Setter
    public static class CodexDeviceOAuth {

        private String command = "codex";
        private String workspaceRoot = "";
        private int startTimeoutSeconds = 30;
        private int authTimeoutSeconds = 900;
    }
}
