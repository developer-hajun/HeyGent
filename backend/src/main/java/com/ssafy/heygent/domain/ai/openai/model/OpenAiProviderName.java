package com.ssafy.heygent.domain.ai.openai.model;

import java.util.Arrays;

import org.springframework.util.StringUtils;

import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

import lombok.Getter;
import lombok.RequiredArgsConstructor;

@Getter
@RequiredArgsConstructor
public enum OpenAiProviderName {

    OPENAI_USER_API_KEY("openai_user_api_key", "api_key"),
    OPENAI_OAUTH("openai_oauth", "oauth"),
    OPENAI_DEV_FALLBACK("openai_dev_fallback", "api_key");

    private final String value;
    private final String authType;

    public static OpenAiProviderName from(String value) {
        if (!StringUtils.hasText(value)) {
            return OPENAI_DEV_FALLBACK;
        }

        return Arrays.stream(values())
            .filter(provider -> provider.value.equals(value.trim()))
            .findFirst()
            .orElseThrow(() -> new CustomException(ErrorCode.OPENAI_PROVIDER_NOT_SUPPORTED));
    }
}
