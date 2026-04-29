package com.ssafy.heygent.domain.auth.controller;

import static org.hamcrest.Matchers.nullValue;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.time.Instant;
import java.util.List;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import com.ssafy.heygent.domain.auth.dto.response.AuthVerificationResponse;
import com.ssafy.heygent.domain.auth.service.AuthVerificationService;

@ExtendWith(MockitoExtension.class)
class AuthVerificationControllerTest {

    private static final String INTERNAL_SERVICE_TOKEN_HEADER = "X-Internal-Service-Token";

    private MockMvc mockMvc;

    @Mock
    private AuthVerificationService authVerificationService;

    @BeforeEach
    void setUp() {
        mockMvc = MockMvcBuilders.standaloneSetup(
            new InternalAuthVerificationController(authVerificationService)
        ).build();
    }

    @Test
    void verifyEndpointReturnsApiResponse() throws Exception {
        AuthVerificationResponse response = AuthVerificationResponse.builder()
            .userId(1L)
            .workspaceKey(null)
            .scopes(List.of("USER"))
            .tokenExpiresAt(Instant.parse("2026-04-29T00:30:00Z"))
            .build();

        when(authVerificationService.verify("internal-service-token", "access-token"))
            .thenReturn(response);

        mockMvc.perform(post("/api/v1/internal/auth/verify")
                .header(INTERNAL_SERVICE_TOKEN_HEADER, "internal-service-token")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"accessToken\":\"access-token\"}"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.status").value(200))
            .andExpect(jsonPath("$.message").value("요청에 성공했습니다."))
            .andExpect(jsonPath("$.data.userId").value(1))
            .andExpect(jsonPath("$.data.workspaceKey").value(nullValue()))
            .andExpect(jsonPath("$.data.scopes[0]").value("USER"))
            .andExpect(jsonPath("$.data.tokenExpiresAt").exists());
    }
}
