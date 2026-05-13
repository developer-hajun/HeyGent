package com.ssafy.heygent.domain.iot.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ssafy.heygent.domain.iot.dto.DisplayEventPayload;
import com.ssafy.heygent.domain.iot.dto.DisplayEventType;
import com.ssafy.heygent.domain.iot.dto.DisplayFocusState;
import com.ssafy.heygent.domain.iot.dto.DisplayIcon;
import com.ssafy.heygent.domain.iot.dto.DisplayPublishResult;
import com.ssafy.heygent.domain.iot.dto.InternalDisplayEventRequest;
import com.ssafy.heygent.domain.iot.repository.DeviceDisplayStateRedisRepository;
import com.ssafy.heygent.domain.iot.repository.IotDeviceRepository;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class DeviceDisplayCoordinatorTest {

    private static final Long USER_ID = 1L;

    @Mock
    private DisplayEventMapper displayEventMapper;

    @Mock
    private DisplayEventPublishService displayEventPublishService;

    @Mock
    private DeviceDisplayStateRedisRepository displayStateRepository;

    @Mock
    private IotDeviceRepository iotDeviceRepository;

    private DeviceDisplayCoordinator coordinator;

    @BeforeEach
    void setUp() {
        coordinator = new DeviceDisplayCoordinator(
            displayEventMapper,
            displayEventPublishService,
            displayStateRepository,
            iotDeviceRepository,
            new ObjectMapper()
        );
    }

    @Test
    void publishInternalKeepsExistingWaitingFocusWhenOtherTaskStepArrives() {
        DisplayEventPayload waitingPayload = payload(DisplayEventType.WAITING, "session-a", "task-a", "step-a", "승인 대기", 10L);
        DisplayEventPayload incomingPayload = payload(DisplayEventType.STEP, "session-b", "task-b", "step-b", "검색 중", 11L);
        InternalDisplayEventRequest request = request(DisplayEventType.STEP, "session-b", "task-b", "step-b", "검색 중");

        when(displayEventMapper.toPayload(
            DisplayEventType.STEP,
            DisplayIcon.SEARCH,
            "session-b",
            "task-b",
            "step-b",
            "검색 중",
            "SEARCHING",
            3000L,
            10,
            "AUTO",
            "RUNNING",
            false
        )).thenReturn(incomingPayload);
        when(displayStateRepository.findFocus(USER_ID))
            .thenReturn(Optional.of(waitingFocus("task-a")));
        when(displayStateRepository.findTaskPayload("task-a"))
            .thenReturn(Optional.of(waitingPayload));
        when(displayEventPublishService.publish(USER_ID, waitingPayload))
            .thenReturn(DisplayPublishResult.published("devices/test/display", 1, waitingPayload));

        DisplayPublishResult result = coordinator.publishInternal(request);

        assertThat(result.payload()).isEqualTo(waitingPayload);
        verify(displayStateRepository).saveTaskPayload(USER_ID, incomingPayload);
        verify(displayEventPublishService).publish(USER_ID, waitingPayload);
        verify(displayEventPublishService, never()).publish(USER_ID, incomingPayload);
    }

    @Test
    void publishInternalDoesNotRestoreWaitingFocusWhenSameTaskMovesForward() {
        DisplayEventPayload incomingPayload = payload(DisplayEventType.STEP, "session-a", "task-a", "step-a2", "작업 중", 12L);
        InternalDisplayEventRequest request = request(DisplayEventType.STEP, "session-a", "task-a", "step-a2", "작업 중");

        when(displayEventMapper.toPayload(
            DisplayEventType.STEP,
            DisplayIcon.SEARCH,
            "session-a",
            "task-a",
            "step-a2",
            "작업 중",
            "SEARCHING",
            3000L,
            10,
            "AUTO",
            "RUNNING",
            false
        )).thenReturn(incomingPayload);
        when(displayStateRepository.findFocus(USER_ID))
            .thenReturn(Optional.of(waitingFocus("task-a")));
        when(displayStateRepository.listActivePayloads(USER_ID))
            .thenReturn(List.of(incomingPayload));
        when(displayEventPublishService.publish(USER_ID, incomingPayload))
            .thenReturn(DisplayPublishResult.published("devices/test/display", 1, incomingPayload));

        DisplayPublishResult result = coordinator.publishInternal(request);

        assertThat(result.payload()).isEqualTo(incomingPayload);
        verify(displayStateRepository, never()).findTaskPayload("task-a");
        verify(displayEventPublishService).publish(USER_ID, incomingPayload);
    }

    @Test
    void publishInternalAlwaysPublishesTaskPayloadEvenWhenDuplicateHashExists() {
        DisplayEventPayload incomingPayload = payload(DisplayEventType.STARTED, "session-a", "task-a", null, "시작", 13L);
        InternalDisplayEventRequest request = new InternalDisplayEventRequest(
            USER_ID,
            DisplayEventType.STARTED,
            DisplayIcon.START,
            "session-a",
            "task-a",
            null,
            "시작",
            "CHECKING_REQUEST",
            2000L,
            20,
            "AUTO",
            "RUNNING",
            true
        );

        when(displayEventMapper.toPayload(
            DisplayEventType.STARTED,
            DisplayIcon.START,
            "session-a",
            "task-a",
            null,
            "시작",
            "CHECKING_REQUEST",
            2000L,
            20,
            "AUTO",
            "RUNNING",
            true
        )).thenReturn(incomingPayload);
        when(displayStateRepository.findFocus(USER_ID)).thenReturn(Optional.empty());
        when(displayEventPublishService.publish(USER_ID, incomingPayload))
            .thenReturn(DisplayPublishResult.published("devices/test/display", 1, incomingPayload));

        DisplayPublishResult result = coordinator.publishInternal(request);

        assertThat(result.published()).isTrue();
        verify(displayEventPublishService).publish(USER_ID, incomingPayload);
        verify(displayStateRepository, never()).findLastSentHash(USER_ID);
    }

    private InternalDisplayEventRequest request(
        DisplayEventType type,
        String sessionId,
        String taskRunId,
        String stepRunId,
        String text
    ) {
        return new InternalDisplayEventRequest(
            USER_ID,
            type,
            DisplayIcon.SEARCH,
            sessionId,
            taskRunId,
            stepRunId,
            text,
            "SEARCHING",
            3000L,
            10,
            "AUTO",
            "RUNNING",
            false
        );
    }

    private DisplayEventPayload payload(
        DisplayEventType type,
        String sessionId,
        String taskRunId,
        String stepRunId,
        String text,
        long seq
    ) {
        return new DisplayEventPayload(
            type,
            sessionId,
            taskRunId,
            stepRunId,
            DisplayIcon.SEARCH,
            text,
            "SEARCHING",
            3000L,
            10,
            "AUTO",
            "RUNNING",
            false,
            seq
        );
    }

    private DisplayFocusState waitingFocus(String taskRunId) {
        return new DisplayFocusState(taskRunId, "WAITING_OVERRIDE", Instant.now().plusSeconds(60).toEpochMilli());
    }
}
