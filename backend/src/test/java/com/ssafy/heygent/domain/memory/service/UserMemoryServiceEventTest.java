package com.ssafy.heygent.domain.memory.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyDouble;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentMatchers.isNull;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.Pageable;
import org.springframework.test.util.ReflectionTestUtils;

import com.ssafy.heygent.domain.memory.dto.request.CreateMemoryRequest;
import com.ssafy.heygent.domain.memory.dto.request.MarkMemoryUsedRequest;
import com.ssafy.heygent.domain.memory.dto.response.UserMemoryResponse;
import com.ssafy.heygent.domain.memory.embedding.MemoryEmbeddingService;
import com.ssafy.heygent.domain.memory.entity.MemoryEventType;
import com.ssafy.heygent.domain.memory.entity.MemoryOperationType;
import com.ssafy.heygent.domain.memory.entity.MemoryScopeType;
import com.ssafy.heygent.domain.memory.entity.MemoryStatus;
import com.ssafy.heygent.domain.memory.entity.MemoryStoreType;
import com.ssafy.heygent.domain.memory.entity.MemoryType;
import com.ssafy.heygent.domain.memory.entity.UserMemory;
import com.ssafy.heygent.domain.memory.entity.UserMemoryEvent;
import com.ssafy.heygent.domain.memory.repository.UserMemoryRepository;
import com.ssafy.heygent.domain.memory.repository.UserMemoryVectorRepository;
import com.ssafy.heygent.global.exception.CustomException;

@ExtendWith(MockitoExtension.class)
class UserMemoryServiceEventTest {

    private static final Long USER_ID = 1L;

    @Mock
    private UserMemoryRepository userMemoryRepository;

    @Mock
    private UserMemoryVectorRepository userMemoryVectorRepository;

    @Mock
    private MemoryEmbeddingService memoryEmbeddingService;

    @Mock
    private MemorySafetyValidator memorySafetyValidator;

    @Mock
    private UserMemoryEventService userMemoryEventService;

    @InjectMocks
    private UserMemoryService userMemoryService;

    @Test
    void createRecordsCreatedEvent() {
        CreateMemoryRequest request = createMemoryRequest();
        UserMemory savedMemory = memory(10L);

        when(userMemoryRepository.findDuplicateActiveMemory(
            eq(USER_ID),
            eq(MemoryStoreType.AGENT_MEMORY),
            eq(MemoryType.FACT),
            eq(MemoryScopeType.GLOBAL),
            eq("사용자는 회의록을 짧게 요약하는 것을 선호한다."),
            eq(MemoryStatus.ACTIVE)
        )).thenReturn(Optional.empty());
        when(userMemoryRepository.save(any(UserMemory.class))).thenReturn(savedMemory);
        when(memoryEmbeddingService.embed(anyString())).thenReturn(List.of(0.1, 0.2));

        UserMemoryResponse response = userMemoryService.create(USER_ID, request);

        assertThat(response.getId()).isEqualTo(10L);
        verify(userMemoryEventService).record(savedMemory, MemoryEventType.CREATED);
        verify(userMemoryVectorRepository).updateEmbedding(eq(10L), eq(List.of(0.1, 0.2)));
    }

    @Test
    void recallRecordsRecalledEvent() {
        UserMemory memory = memory(20L);
        when(userMemoryRepository.findRecallCandidates(
            eq(USER_ID),
            eq(MemoryStatus.ACTIVE),
            anyDouble(),
            anyDouble(),
            any(LocalDateTime.class),
            isNull(),
            isNull(),
            isNull(),
            eq(MemoryScopeType.SESSION),
            any(Pageable.class)
        )).thenReturn(List.of(memory));

        List<UserMemoryResponse> responses = userMemoryService.recall(
            USER_ID,
            5,
            null,
            null,
            null,
            null,
            null,
            null,
            null,
            null,
            null
        );

        assertThat(responses).hasSize(1);
        assertThat(memory.getAccessCount()).isEqualTo(1L);
        verify(userMemoryEventService).record(
            eq(memory),
            eq(MemoryEventType.RECALLED),
            isNull(),
            eq(Map.of("queryProvided", false, "limit", 5))
        );
    }

    @Test
    void deleteRecordsDeletedEvent() {
        UserMemory memory = memory(30L);
        when(userMemoryRepository.findById(30L)).thenReturn(Optional.of(memory));

        userMemoryService.delete(USER_ID, 30L);

        assertThat(memory.getStatus()).isEqualTo(MemoryStatus.DELETED);
        verify(userMemoryEventService).record(memory, MemoryEventType.DELETED);
    }

    @Test
    void markUsedRecordsUsedEvent() {
        UserMemory memory = memory(40L);
        MarkMemoryUsedRequest request = new MarkMemoryUsedRequest();
        ReflectionTestUtils.setField(request, "usefulnessScore", 0.8);
        when(userMemoryRepository.findById(40L)).thenReturn(Optional.of(memory));

        UserMemoryResponse response = userMemoryService.markUsed(USER_ID, 40L, request);

        assertThat(response.getUsedCount()).isEqualTo(1L);
        assertThat(response.getUsefulnessScore()).isEqualTo(0.8);
        verify(userMemoryEventService).record(memory, MemoryEventType.USED, 0.8, Map.of());
    }

    @Test
    void getMemoryEventsReturnsOwnedMemoryEvents() {
        UserMemory memory = memory(45L);
        UserMemoryEvent event = memoryEvent(100L, 45L, MemoryEventType.RECALLED);
        when(userMemoryRepository.findById(45L)).thenReturn(Optional.of(memory));
        when(userMemoryEventService.findEvents(USER_ID, 45L)).thenReturn(List.of(event));

        var responses = userMemoryService.getMemoryEvents(USER_ID, 45L);

        assertThat(responses).hasSize(1);
        assertThat(responses.get(0).getId()).isEqualTo(100L);
        assertThat(responses.get(0).getMemoryId()).isEqualTo(45L);
        assertThat(responses.get(0).getEventType()).isEqualTo(MemoryEventType.RECALLED);
        assertThat(responses.get(0).getTaskRunId()).isEqualTo("task-1");
        assertThat(responses.get(0).getMetadata()).isEqualTo(Map.of("queryProvided", true));
    }

    @Test
    void getMemoryEventsRejectsOtherUserMemory() {
        UserMemory memory = UserMemory.builder()
            .id(46L)
            .userId(999L)
            .memoryType(MemoryType.FACT)
            .content("다른 사용자 기억")
            .importance(0.8)
            .confidence(0.9)
            .status(MemoryStatus.ACTIVE)
            .build();
        when(userMemoryRepository.findById(46L)).thenReturn(Optional.of(memory));

        assertThatThrownBy(() -> userMemoryService.getMemoryEvents(USER_ID, 46L))
            .isInstanceOf(CustomException.class);
    }

    @Test
    void updateRecordsUpdatedAndInvalidatedEvents() {
        CreateMemoryRequest request = createMemoryRequest();
        ReflectionTestUtils.setField(request, "operationType", MemoryOperationType.UPDATE);
        ReflectionTestUtils.setField(request, "targetMemoryId", 50L);
        UserMemory targetMemory = memory(50L);

        when(memoryEmbeddingService.embed(anyString())).thenReturn(List.of(0.1, 0.2));
        when(userMemoryRepository.findById(50L)).thenReturn(Optional.of(targetMemory));
        when(userMemoryRepository.save(any(UserMemory.class))).thenAnswer(invocation -> {
            UserMemory savedMemory = invocation.getArgument(0);
            ReflectionTestUtils.setField(savedMemory, "id", 51L);
            return savedMemory;
        });

        UserMemoryResponse response = userMemoryService.create(USER_ID, request);

        assertThat(response.getId()).isEqualTo(51L);
        verify(userMemoryEventService).record(any(UserMemory.class), eq(MemoryEventType.UPDATED));
        verify(userMemoryEventService).record(
            eq(targetMemory),
            eq(MemoryEventType.INVALIDATED),
            isNull(),
            eq(Map.of("supersededByMemoryId", 51L, "operationType", MemoryEventType.UPDATED.name()))
        );
    }

    @Test
    void mergeRecordsMergedAndInvalidatedEvents() {
        CreateMemoryRequest request = createMemoryRequest();
        ReflectionTestUtils.setField(request, "operationType", MemoryOperationType.MERGE);
        ReflectionTestUtils.setField(request, "targetMemoryId", 60L);
        UserMemory targetMemory = memory(60L);

        when(memoryEmbeddingService.embed(anyString())).thenReturn(List.of(0.1, 0.2));
        when(userMemoryRepository.findById(60L)).thenReturn(Optional.of(targetMemory));
        when(userMemoryRepository.save(any(UserMemory.class))).thenAnswer(invocation -> {
            UserMemory savedMemory = invocation.getArgument(0);
            ReflectionTestUtils.setField(savedMemory, "id", 61L);
            return savedMemory;
        });

        UserMemoryResponse response = userMemoryService.create(USER_ID, request);

        assertThat(response.getId()).isEqualTo(61L);
        verify(userMemoryEventService).record(any(UserMemory.class), eq(MemoryEventType.MERGED));
        verify(userMemoryEventService).record(
            eq(targetMemory),
            eq(MemoryEventType.INVALIDATED),
            isNull(),
            eq(Map.of("supersededByMemoryId", 61L, "operationType", MemoryEventType.MERGED.name()))
        );
    }

    @Test
    void invalidateRecordsInvalidatedEvent() {
        CreateMemoryRequest request = createMemoryRequest();
        ReflectionTestUtils.setField(request, "operationType", MemoryOperationType.INVALIDATE);
        ReflectionTestUtils.setField(request, "targetMemoryId", 70L);
        UserMemory targetMemory = memory(70L);
        when(userMemoryRepository.findById(70L)).thenReturn(Optional.of(targetMemory));

        UserMemoryResponse response = userMemoryService.create(USER_ID, request);

        assertThat(response.getId()).isEqualTo(70L);
        assertThat(response.getStatus()).isEqualTo(MemoryStatus.INACTIVE);
        verify(userMemoryEventService).record(targetMemory, MemoryEventType.INVALIDATED);
    }

    private CreateMemoryRequest createMemoryRequest() {
        CreateMemoryRequest request = new CreateMemoryRequest();
        ReflectionTestUtils.setField(request, "memoryType", MemoryType.FACT);
        ReflectionTestUtils.setField(request, "scopeType", MemoryScopeType.GLOBAL);
        ReflectionTestUtils.setField(request, "content", "사용자는 회의록을 짧게 요약하는 것을 선호한다.");
        ReflectionTestUtils.setField(request, "summary", "짧은 회의록 요약 선호");
        ReflectionTestUtils.setField(request, "metadata", Map.of());
        ReflectionTestUtils.setField(request, "importance", 0.8);
        ReflectionTestUtils.setField(request, "confidence", 0.9);
        return request;
    }

    private UserMemory memory(Long id) {
        return UserMemory.builder()
            .id(id)
            .userId(USER_ID)
            .storeType(MemoryStoreType.AGENT_MEMORY)
            .memoryType(MemoryType.FACT)
            .scopeType(MemoryScopeType.GLOBAL)
            .content("사용자는 회의록을 짧게 요약하는 것을 선호한다.")
            .summary("짧은 회의록 요약 선호")
            .metadata(Map.of())
            .embeddingText("[0.1,0.2]")
            .importance(0.8)
            .confidence(0.9)
            .status(MemoryStatus.ACTIVE)
            .validFrom(LocalDateTime.now().minusDays(1))
            .accessCount(0L)
            .usedCount(0L)
            .usefulnessScore(0.0)
            .build();
    }

    private UserMemoryEvent memoryEvent(Long id, Long memoryId, MemoryEventType eventType) {
        return UserMemoryEvent.builder()
            .id(id)
            .memoryId(memoryId)
            .userId(USER_ID)
            .eventType(eventType)
            .taskRunId("task-1")
            .messageId("msg-1")
            .score(0.8)
            .metadata(Map.of("queryProvided", true))
            .createdAt(LocalDateTime.of(2026, 5, 11, 15, 30))
            .build();
    }
}
