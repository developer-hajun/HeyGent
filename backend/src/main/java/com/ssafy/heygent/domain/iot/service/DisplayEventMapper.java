package com.ssafy.heygent.domain.iot.service;

import com.ssafy.heygent.domain.iot.dto.DisplayEventPayload;
import com.ssafy.heygent.domain.iot.dto.DisplayEventType;
import com.ssafy.heygent.domain.iot.dto.DisplayIcon;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;

import java.util.concurrent.atomic.AtomicLong;

@Service
public class DisplayEventMapper {

    private static final int MAX_TEXT_LENGTH = 12;

    private final AtomicLong sequence = new AtomicLong(0);

    public DisplayEventPayload toPayload(DisplayEventType type, String taskRunId, String text) {
        DisplayEventType resolvedType = type == null ? DisplayEventType.INFO : type;
        String resolvedText = compactText(text, defaultText(resolvedType));

        return new DisplayEventPayload(
            resolvedType,
            taskRunId,
            defaultIcon(resolvedType),
            resolvedText,
            defaultTtlMs(resolvedType),
            sequence.incrementAndGet()
        );
    }

    private String compactText(String text, String fallback) {
        String value = StringUtils.hasText(text) ? text.trim() : fallback;
        if (value.length() <= MAX_TEXT_LENGTH) {
            return value;
        }
        return value.substring(0, MAX_TEXT_LENGTH);
    }

    private String defaultText(DisplayEventType type) {
        return switch (type) {
            case STARTED -> "시작";
            case STEP -> "진행 중";
            case WAITING -> "확인 필요";
            case DONE -> "완료";
            case FAILED -> "실패";
            case INFO -> "알림";
        };
    }

    private DisplayIcon defaultIcon(DisplayEventType type) {
        return switch (type) {
            case STARTED -> DisplayIcon.START;
            case STEP -> DisplayIcon.THINKING;
            case WAITING -> DisplayIcon.QUESTION;
            case DONE -> DisplayIcon.HAPPY;
            case FAILED -> DisplayIcon.SAD;
            case INFO -> DisplayIcon.INFO;
        };
    }

    private long defaultTtlMs(DisplayEventType type) {
        return switch (type) {
            case STARTED -> 2000L;
            case STEP -> 3000L;
            case WAITING -> 0L;
            case DONE, FAILED -> 5000L;
            case INFO -> 3000L;
        };
    }
}
