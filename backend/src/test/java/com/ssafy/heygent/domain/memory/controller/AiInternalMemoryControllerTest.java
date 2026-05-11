package com.ssafy.heygent.domain.memory.controller;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentMatchers.isNull;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.data.jpa.mapping.JpaMetamodelMappingContext;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ssafy.heygent.domain.memory.dto.request.CreateMemoryRequest;
import com.ssafy.heygent.domain.memory.dto.response.UserMemoryResponse;
import com.ssafy.heygent.domain.memory.entity.MemoryScopeType;
import com.ssafy.heygent.domain.memory.entity.MemoryStoreType;
import com.ssafy.heygent.domain.memory.entity.MemoryType;
import com.ssafy.heygent.domain.memory.service.UserMemoryService;
import com.ssafy.heygent.global.config.jwt.JwtProvider;
import com.ssafy.heygent.global.config.security.AiInternalAuthenticationFilter;
import com.ssafy.heygent.global.config.security.AiInternalProperties;
import com.ssafy.heygent.global.config.security.JwtAuthenticationFilter;
import com.ssafy.heygent.global.config.security.SecurityConfig;

@WebMvcTest(AiInternalMemoryController.class)
@Import({SecurityConfig.class, JwtAuthenticationFilter.class, AiInternalAuthenticationFilter.class})
class AiInternalMemoryControllerTest {

    private static final String INTERNAL_TOKEN = "internal-test-token";
    private static final Long USER_ID = 1L;

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @MockBean
    private UserMemoryService userMemoryService;

    @MockBean
    private JwtProvider jwtProvider;

    @MockBean
    private AiInternalProperties aiInternalProperties;

    @MockBean
    private JpaMetamodelMappingContext jpaMetamodelMappingContext;

    @BeforeEach
    void setUp() {
        when(aiInternalProperties.getToken()).thenReturn(INTERNAL_TOKEN);
    }

    @Test
    void recallRequiresInternalToken() throws Exception {
        mockMvc.perform(get("/internal/ai/memories/recall")
                .param("userId", USER_ID.toString())
                .param("query", "회의록 요약"))
            .andExpect(status().isUnauthorized());
    }

    @Test
    void recallCallsServiceWithUserIdAndFilters() throws Exception {
        when(userMemoryService.recall(
            eq(USER_ID),
            eq(5),
            eq("회의록 요약"),
            eq(MemoryStoreType.AGENT_MEMORY),
            eq(MemoryType.FACT),
            eq(MemoryScopeType.WORKSPACE),
            eq("workspace-a"),
            isNull(),
            eq("resource-a"),
            eq(List.of("project")),
            eq(List.of("task_state"))
        )).thenReturn(List.of(memoryResponse(10L)));

        mockMvc.perform(get("/internal/ai/memories/recall")
                .header("Authorization", "Bearer " + INTERNAL_TOKEN)
                .param("userId", USER_ID.toString())
                .param("query", "회의록 요약")
                .param("limit", "5")
                .param("storeType", "AGENT_MEMORY")
                .param("memoryType", "FACT")
                .param("scopeType", "WORKSPACE")
                .param("workspaceKey", "workspace-a")
                .param("resourceId", "resource-a")
                .param("tags", "project")
                .param("metadataCategories", "task_state"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.data[0].id").value(10L))
            .andExpect(jsonPath("$.data[0].content").value("사용자는 회의록을 짧게 요약하는 것을 선호한다."));
    }

    @Test
    void createCandidatesCallsServiceWithUserId() throws Exception {
        when(userMemoryService.createCandidates(eq(USER_ID), any(List.class)))
            .thenReturn(List.of(memoryResponse(11L)));

        mockMvc.perform(post("/internal/ai/memories/candidates")
                .header("Authorization", "Bearer " + INTERNAL_TOKEN)
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "userId": 1,
                      "candidates": [
                        {
                          "memoryType": "PREFERENCE",
                          "scopeType": "GLOBAL",
                          "content": "사용자는 짧은 답변을 선호한다.",
                          "summary": "짧은 답변 선호",
                          "metadata": {},
                          "importance": 0.8,
                          "confidence": 0.9
                        }
                      ]
                    }
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.data[0].id").value(11L));

        verify(userMemoryService).createCandidates(eq(USER_ID), any(List.class));
    }

    @Test
    void markUsedCallsServiceWithUserIdAndScore() throws Exception {
        when(userMemoryService.markUsed(USER_ID, 10L, 0.75)).thenReturn(memoryResponse(10L));

        mockMvc.perform(post("/internal/ai/memories/{memoryId}/used", 10L)
                .header("Authorization", "Bearer " + INTERNAL_TOKEN)
                .contentType(MediaType.APPLICATION_JSON)
                .content(objectMapper.writeValueAsString(Map.of(
                    "userId", USER_ID,
                    "usefulnessScore", 0.75
                ))))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.data.id").value(10L));

        verify(userMemoryService).markUsed(USER_ID, 10L, 0.75);
    }

    private UserMemoryResponse memoryResponse(Long memoryId) {
        return UserMemoryResponse.builder()
            .id(memoryId)
            .storeType(MemoryStoreType.AGENT_MEMORY)
            .memoryType(MemoryType.FACT)
            .scopeType(MemoryScopeType.GLOBAL)
            .content("사용자는 회의록을 짧게 요약하는 것을 선호한다.")
            .summary("짧은 회의록 요약 선호")
            .metadata(Map.of())
            .importance(0.8)
            .confidence(0.9)
            .build();
    }
}
