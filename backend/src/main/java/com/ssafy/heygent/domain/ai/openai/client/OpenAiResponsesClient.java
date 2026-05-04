package com.ssafy.heygent.domain.ai.openai.client;

import java.time.Duration;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

import com.ssafy.heygent.domain.ai.openai.config.OpenAiProperties;
import com.ssafy.heygent.domain.ai.openai.dto.OpenAiResponsesCommand;
import com.ssafy.heygent.domain.ai.openai.dto.OpenAiResponsesResult;
import com.ssafy.heygent.domain.ai.openai.dto.OpenAiUsage;
import com.ssafy.heygent.domain.ai.openai.model.OpenAiProviderName;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

@Slf4j
@Component
@RequiredArgsConstructor
public class OpenAiResponsesClient {

    private static final String RESPONSES_PATH = "/responses";

    private final OpenAiProperties properties;

    public OpenAiResponsesResult callWithApiKey(
        OpenAiResponsesCommand command,
        String model,
        String apiKey,
        OpenAiProviderName providerName
    ) {
        Map<String, Object> requestBody = buildRequestBody(command, model);

        try {
            Map<String, Object> responseBody = restClient(apiKey).post()
                .uri(RESPONSES_PATH)
                .body(requestBody)
                .retrieve()
                .body(new ParameterizedTypeReference<>() {
                });

            return toResult(responseBody == null ? Map.of() : responseBody, model, providerName);
        } catch (RestClientException exception) {
            log.warn("Failed to call OpenAI Responses API. provider={}, model={}", providerName.getValue(), model,
                exception);
            throw new CustomException(ErrorCode.OPENAI_CALL_FAILED);
        }
    }

    private RestClient restClient(String apiKey) {
        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        requestFactory.setConnectTimeout(Duration.ofSeconds(properties.getTimeoutSeconds()));
        requestFactory.setReadTimeout(Duration.ofSeconds(properties.getTimeoutSeconds()));

        return RestClient.builder()
            .requestFactory(requestFactory)
            .baseUrl(properties.getRestApiBaseUrl())
            .defaultHeader(HttpHeaders.AUTHORIZATION, "Bearer " + apiKey)
            .defaultHeader(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
            .build();
    }

    private Map<String, Object> buildRequestBody(OpenAiResponsesCommand command, String model) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("model", model);
        body.put("store", false);
        body.put("input", command.input());
        if (command.tools() != null && !command.tools().isEmpty()) {
            body.put("tools", command.tools());
        }
        if (command.toolChoice() != null) {
            body.put("tool_choice", command.toolChoice());
        }
        return body;
    }

    @SuppressWarnings("unchecked")
    private OpenAiResponsesResult toResult(
        Map<String, Object> responseBody,
        String requestedModel,
        OpenAiProviderName providerName
    ) {
        List<Map<String, Object>> toolCalls = extractToolCalls(responseBody);
        String outputText = extractOutputText(responseBody);
        String model = valueAsString(responseBody.get("model"), requestedModel);
        String finishReason = toolCalls.isEmpty()
            ? valueAsString(responseBody.get("status"), outputText.isBlank() ? null : "stop")
            : "tool_calls";

        return new OpenAiResponsesResult(
            providerName.getValue(),
            providerName.getAuthType(),
            model,
            valueAsString(responseBody.get("id"), null),
            outputText,
            toolCalls,
            finishReason,
            OpenAiUsage.from((Map<String, Object>)responseBody.get("usage")),
            responseBody
        );
    }

    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> extractToolCalls(Map<String, Object> responseBody) {
        List<Map<String, Object>> toolCalls = new ArrayList<>();
        Object output = responseBody.get("output");
        if (!(output instanceof List<?> outputItems)) {
            return toolCalls;
        }

        for (Object item : outputItems) {
            if (!(item instanceof Map<?, ?> rawItem)) {
                continue;
            }
            Map<String, Object> outputItem = (Map<String, Object>)rawItem;
            String type = valueAsString(outputItem.get("type"), "");
            if ("function_call".equals(type) || "tool_call".equals(type)) {
                toolCalls.add(outputItem);
                continue;
            }
            Object nestedToolCalls = outputItem.get("tool_calls");
            if (nestedToolCalls instanceof List<?> nestedItems) {
                for (Object nested : nestedItems) {
                    if (nested instanceof Map<?, ?> nestedMap) {
                        toolCalls.add((Map<String, Object>)nestedMap);
                    }
                }
            }
        }
        return toolCalls;
    }

    @SuppressWarnings("unchecked")
    private String extractOutputText(Map<String, Object> responseBody) {
        String directOutputText = valueAsString(responseBody.get("output_text"), "");
        if (!directOutputText.isBlank()) {
            return directOutputText;
        }

        Object output = responseBody.get("output");
        if (!(output instanceof List<?> outputItems)) {
            return "";
        }

        List<String> texts = new ArrayList<>();
        for (Object item : outputItems) {
            if (!(item instanceof Map<?, ?> rawItem)) {
                continue;
            }
            Map<String, Object> outputItem = (Map<String, Object>)rawItem;
            Object content = outputItem.get("content");
            if (!(content instanceof List<?> contentItems)) {
                continue;
            }
            for (Object contentItem : contentItems) {
                if (contentItem instanceof Map<?, ?> rawContentItem) {
                    String text = valueAsString(((Map<String, Object>)rawContentItem).get("text"), "");
                    if (!text.isBlank()) {
                        texts.add(text);
                    }
                }
            }
        }
        return String.join("\n", texts);
    }

    private String valueAsString(Object value, String defaultValue) {
        if (value == null) {
            return defaultValue;
        }
        return String.valueOf(value);
    }
}
