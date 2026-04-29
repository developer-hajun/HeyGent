package com.ssafy.heygent.domain.iot.dto;

import com.fasterxml.jackson.annotation.JsonValue;
import lombok.Getter;
import lombok.RequiredArgsConstructor;

@Getter
@RequiredArgsConstructor
public enum DisplayIcon {
    START("start"),
    THINKING("thinking"),
    QUESTION("question"),
    HAPPY("happy"),
    SAD("sad"),
    INFO("info");

    @JsonValue
    private final String value;
}
