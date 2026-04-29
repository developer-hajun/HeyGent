package com.ssafy.heygent.domain.iot.dto;

import com.fasterxml.jackson.annotation.JsonCreator;
import com.fasterxml.jackson.annotation.JsonValue;
import lombok.Getter;
import lombok.RequiredArgsConstructor;

@Getter
@RequiredArgsConstructor
public enum DisplayIcon {
    START("start"),
    THINKING("thinking"),
    SEARCH("search"),
    WRITE("write"),
    SEND("send"),
    TOOL("tool"),
    CODE("code"),
    REVIEW("review"),
    DELEGATE("delegate"),
    QUESTION("question"),
    SUCCESS("success"),
    ERROR("error"),
    INFO("info"),
    WAIT("wait"),
    CANCEL("cancel");

    @JsonValue
    private final String value;

    @JsonCreator
    public static DisplayIcon fromValue(String value) {
        if (value == null) {
            return null;
        }

        for (DisplayIcon icon : values()) {
            if (icon.value.equalsIgnoreCase(value) || icon.name().equalsIgnoreCase(value)) {
                return icon;
            }
        }

        throw new IllegalArgumentException("Unknown display icon: " + value);
    }
}
