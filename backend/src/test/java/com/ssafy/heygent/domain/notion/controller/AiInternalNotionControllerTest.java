package com.ssafy.heygent.domain.notion.controller;

import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
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

import com.ssafy.heygent.domain.notion.dto.response.NotionExecuteCommandResponse;
import com.ssafy.heygent.domain.notion.service.NotionApiService;
import com.ssafy.heygent.global.config.jwt.JwtProvider;
import com.ssafy.heygent.global.config.security.AiInternalAuthenticationFilter;
import com.ssafy.heygent.global.config.security.AiInternalProperties;
import com.ssafy.heygent.global.config.security.JwtAuthenticationFilter;
import com.ssafy.heygent.global.config.security.SecurityConfig;

@WebMvcTest(AiInternalNotionController.class)
@Import({SecurityConfig.class, JwtAuthenticationFilter.class, AiInternalAuthenticationFilter.class})
class AiInternalNotionControllerTest {

    private static final String INTERNAL_TOKEN = "internal-test-token";
    private static final Long USER_ID = 1L;

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private NotionApiService notionApiService;

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
    void executeRequiresInternalToken() throws Exception {
        mockMvc.perform(post("/internal/ai/notion/execute")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "userId": 1,
                      "commands": [
                        {
                          "method": "POST",
                          "endpoint": "/v1/search",
                          "notionVersion": "2026-03-11",
                          "params": {"query": "테스트용입니다"}
                        }
                      ]
                    }
                    """))
            .andExpect(status().isUnauthorized());
    }

    @Test
    void executeReusesNotionBatchServiceWithRequestUserId() throws Exception {
        when(notionApiService.executeBatch(eq(USER_ID), eq(USER_ID), anyList()))
            .thenReturn(List.of(NotionExecuteCommandResponse.success(
                0,
                USER_ID,
                "POST",
                "/v1/search",
                "2026-03-11",
                Map.of("object", "list")
            )));

        mockMvc.perform(post("/internal/ai/notion/execute")
                .header("Authorization", "Bearer " + INTERNAL_TOKEN)
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                    {
                      "userId": 1,
                      "commands": [
                        {
                          "method": "POST",
                          "endpoint": "/v1/search",
                          "notionVersion": "2026-03-11",
                          "params": {"query": "테스트용입니다"}
                        }
                      ]
                    }
                    """))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.data[0].success").value(true))
            .andExpect(jsonPath("$.data[0].endpoint").value("/v1/search"));

        verify(notionApiService).executeBatch(eq(USER_ID), eq(USER_ID), anyList());
    }
}
