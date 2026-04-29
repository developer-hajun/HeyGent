package com.ssafy.heygent.domain.iot.service;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

import com.ssafy.heygent.domain.iot.dto.DisplayEventPayload;
import com.ssafy.heygent.domain.iot.dto.DisplayEventType;
import com.ssafy.heygent.domain.iot.dto.DisplayIcon;

class DisplayEventMapperTest {

    private final DisplayEventMapper displayEventMapper = new DisplayEventMapper();

    @Test
    void toPayloadUsesSessionAndStepRunIds() {
        DisplayEventPayload payload = displayEventMapper.toPayload(
            DisplayEventType.STEP,
            DisplayIcon.SEARCH,
            "session_test_001",
            "step_test_001",
            "searching"
        );

        assertThat(payload.type()).isEqualTo(DisplayEventType.STEP);
        assertThat(payload.icon()).isEqualTo(DisplayIcon.SEARCH);
        assertThat(payload.sessionId()).isEqualTo("session_test_001");
        assertThat(payload.stepRunId()).isEqualTo("step_test_001");
        assertThat(payload.text()).isEqualTo("searching");
        assertThat(payload.ttlMs()).isEqualTo(3000L);
        assertThat(payload.seq()).isPositive();
    }

    @Test
    void toPayloadMapsTerminalTypesToStateIcons() {
        DisplayEventPayload done = displayEventMapper.toPayload(
            DisplayEventType.DONE,
            "session_test_001",
            "step_done_001",
            null
        );
        DisplayEventPayload failed = displayEventMapper.toPayload(
            DisplayEventType.FAILED,
            "session_test_001",
            "step_failed_001",
            null
        );
        DisplayEventPayload canceled = displayEventMapper.toPayload(
            DisplayEventType.CANCELED,
            "session_test_001",
            "step_canceled_001",
            null
        );

        assertThat(done.icon()).isEqualTo(DisplayIcon.SUCCESS);
        assertThat(done.text()).isEqualTo("done");
        assertThat(failed.icon()).isEqualTo(DisplayIcon.ERROR);
        assertThat(failed.text()).isEqualTo("failed");
        assertThat(canceled.icon()).isEqualTo(DisplayIcon.CANCEL);
        assertThat(canceled.text()).isEqualTo("canceled");
    }

    @Test
    void toPayloadCompactsTextForSmallDisplay() {
        DisplayEventPayload payload = displayEventMapper.toPayload(
            DisplayEventType.INFO,
            "session_test_001",
            "step_info_001",
            "abcdefghijklmnop"
        );

        assertThat(payload.text()).isEqualTo("abcdefghijkl");
    }
}
