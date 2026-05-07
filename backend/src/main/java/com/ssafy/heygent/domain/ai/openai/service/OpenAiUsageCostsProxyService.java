package com.ssafy.heygent.domain.ai.openai.service;

import java.time.LocalDate;
import java.time.ZoneOffset;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.ssafy.heygent.domain.ai.dto.response.OpenAiUsageCostsProxyResponse;
import com.ssafy.heygent.domain.ai.openai.client.OpenAiUsageCostsClient;
import com.ssafy.heygent.domain.ai.openai.config.OpenAiProperties;
import com.ssafy.heygent.domain.ai.openai.model.OpenAiProviderName;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
public class OpenAiUsageCostsProxyService {

    private final OpenAiProperties properties;
    private final OpenAiRuntimePolicyService runtimePolicyService;
    private final OpenAiApiKeyService openAiApiKeyService;
    private final OpenAiOAuthService openAiOAuthService;
    private final OpenAiUsageCostsClient openAiUsageCostsClient;

    @Transactional
    public OpenAiUsageCostsProxyResponse getUsage(Long userId, String providerNameValue, LocalDate from, LocalDate to) {
        OpenAiProviderName providerName = OpenAiProviderName.from(providerNameValue);
        if (!providerName.supportsUsageQuery()) {
            throw new CustomException(ErrorCode.OPENAI_PROVIDER_NOT_SUPPORTED);
        }
        String credential = resolveCredential(userId, providerName);
        long startTime = toStartTime(from);
        Long endTime = toEndTime(to);

        return OpenAiUsageCostsProxyResponse.builder()
            .providerName(providerName.getValue())
            .usage(openAiUsageCostsClient.getUsage(credential, startTime, endTime))
            .costs(openAiUsageCostsClient.getCosts(credential, startTime, endTime))
            .build();
    }

    private String resolveCredential(Long userId, OpenAiProviderName providerName) {
        if (providerName == OpenAiProviderName.OPENAI_API_KEY) {
            return openAiApiKeyService.resolveApiKey(userId, providerName);
        }
        if (providerName == OpenAiProviderName.OPENAI_OAUTH) {
            return openAiOAuthService.resolveAccessTokenCredential(userId).accessToken();
        }
        if (providerName == OpenAiProviderName.OPENAI_DEV_FALLBACK) {
            runtimePolicyService.validateDevFallbackAvailable();
            return properties.getApiKey();
        }
        throw new CustomException(ErrorCode.OPENAI_PROVIDER_NOT_SUPPORTED);
    }

    private long toStartTime(LocalDate from) {
        LocalDate date = from == null ? LocalDate.now(ZoneOffset.UTC).minusDays(30) : from;
        return date.atStartOfDay().toEpochSecond(ZoneOffset.UTC);
    }

    private Long toEndTime(LocalDate to) {
        if (to == null) {
            return null;
        }
        return to.plusDays(1).atStartOfDay().toEpochSecond(ZoneOffset.UTC);
    }
}
