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

    OPENAI_API("openai_api", "api_key"),
    OPENAI_OAUTH("openai_oauth", "oauth");

    private final String value;
    private final String authType;

    public static OpenAiProviderName from(String value) {
        if (!StringUtils.hasText(value)) {
            return OPENAI_API;
        }

        return Arrays.stream(values())
            .filter(provider -> provider.value.equals(value.trim()))
            .findFirst()
            .orElseThrow(() -> new CustomException(ErrorCode.OPENAI_PROVIDER_NOT_SUPPORTED));
    }
}
