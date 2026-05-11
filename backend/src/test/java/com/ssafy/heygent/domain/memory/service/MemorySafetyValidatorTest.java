package com.ssafy.heygent.domain.memory.service;

import static org.assertj.core.api.Assertions.assertThatCode;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import java.util.Map;

import org.junit.jupiter.api.Test;

import com.ssafy.heygent.global.exception.CustomException;

class MemorySafetyValidatorTest {

    private final MemorySafetyValidator validator = new MemorySafetyValidator();

    @Test
    void validateAllowsMemoryCategoryMetadata() {
        assertThatCode(() -> validator.validate(
            "장기기억 구현은 후보 분류 작업이 남아 있다.",
            "장기기억 task state",
            Map.of(
                "source", "ai.writeback",
                "category", "task_state",
                "sensitivity", "low",
                "ttl", "short",
                "sourceTimestamp", "2026-05-11T10:30:00",
                "eventTime", "2026-05-11T10:00:00",
                "reason", "사용자가 후속 작업에 필요한 구현 상태를 명시함"
            )
        )).doesNotThrowAnyException();
    }

    @Test
    void validateRejectsUnknownMemoryCategory() {
        assertThatThrownBy(() -> validator.validate(
            "장기기억 구현은 후보 분류 작업이 남아 있다.",
            "장기기억 task state",
            Map.of("source", "ai.writeback", "category", "temporary")
        )).isInstanceOf(CustomException.class);
    }

    @Test
    void validateRejectsUnknownMetadataKey() {
        assertThatThrownBy(() -> validator.validate(
            "사용자는 짧은 답변을 선호한다.",
            "짧은 답변 선호",
            Map.of("unknown", "value")
        )).isInstanceOf(CustomException.class);
    }
}
