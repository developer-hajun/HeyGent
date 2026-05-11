package com.ssafy.heygent.domain.memory.controller;

import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.user;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.data.jpa.mapping.JpaMetamodelMappingContext;
import org.springframework.test.web.servlet.MockMvc;

import com.ssafy.heygent.domain.memory.dto.response.UserMemoryEventResponse;
import com.ssafy.heygent.domain.memory.entity.MemoryEventType;
import com.ssafy.heygent.domain.memory.service.UserMemoryService;
import com.ssafy.heygent.global.config.jwt.JwtProvider;
import com.ssafy.heygent.global.config.security.AiInternalAuthenticationFilter;
import com.ssafy.heygent.global.config.security.AiInternalProperties;
import com.ssafy.heygent.global.config.security.CustomUserPrincipal;
import com.ssafy.heygent.global.config.security.JwtAuthenticationFilter;
import com.ssafy.heygent.global.config.security.SecurityConfig;

@WebMvcTest(UserMemoryController.class)
@Import({SecurityConfig.class, JwtAuthenticationFilter.class, AiInternalAuthenticationFilter.class})
class UserMemoryControllerTest {

    private static final Long USER_ID = 1L;

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private UserMemoryService userMemoryService;

    @MockBean
    private JwtProvider jwtProvider;

    @MockBean
    private AiInternalProperties aiInternalProperties;

    @MockBean
    private JpaMetamodelMappingContext jpaMetamodelMappingContext;

    @Test
    void getMemoryEventsRequiresAuthentication() throws Exception {
        mockMvc.perform(get("/api/v1/memories/{memoryId}/events", 10L))
            .andExpect(status().is4xxClientError());
    }

    @Test
    void getMemoryEventsCallsServiceWithAuthenticatedUser() throws Exception {
        when(userMemoryService.getMemoryEvents(USER_ID, 10L)).thenReturn(List.of(eventResponse()));

        mockMvc.perform(get("/api/v1/memories/{memoryId}/events", 10L)
                .with(user(new CustomUserPrincipal(USER_ID))))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.data[0].id").value(100L))
            .andExpect(jsonPath("$.data[0].memoryId").value(10L))
            .andExpect(jsonPath("$.data[0].eventType").value("RECALLED"))
            .andExpect(jsonPath("$.data[0].taskRunId").value("task-1"))
            .andExpect(jsonPath("$.data[0].metadata.queryProvided").value(true));

        verify(userMemoryService).getMemoryEvents(USER_ID, 10L);
    }

    private UserMemoryEventResponse eventResponse() {
        return UserMemoryEventResponse.builder()
            .id(100L)
            .memoryId(10L)
            .eventType(MemoryEventType.RECALLED)
            .taskRunId("task-1")
            .messageId("msg-1")
            .score(0.8)
            .metadata(Map.of("queryProvided", true))
            .createdAt(LocalDateTime.of(2026, 5, 11, 15, 30))
            .build();
    }
}
