package com.ssafy.heygent.global.config.security;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockFilterChain;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.security.core.context.SecurityContextHolder;

import com.fasterxml.jackson.databind.ObjectMapper;

class AiInternalAuthenticationFilterTest {

    private static final String INTERNAL_TOKEN = "internal-test-token";

    @AfterEach
    void tearDown() {
        SecurityContextHolder.clearContext();
    }

    @Test
    void internalAiPathRequiresInternalToken() throws Exception {
        AiInternalAuthenticationFilter filter = filter(INTERNAL_TOKEN);
        MockHttpServletRequest request = new MockHttpServletRequest("POST", "/internal/ai/auth/validate");
        MockHttpServletResponse response = new MockHttpServletResponse();
        MockFilterChain filterChain = new MockFilterChain();

        filter.doFilter(request, response, filterChain);

        assertThat(response.getStatus()).isEqualTo(401);
        assertThat(SecurityContextHolder.getContext().getAuthentication()).isNull();
    }

    @Test
    void internalAiPathAuthenticatesWithValidInternalToken() throws Exception {
        AiInternalAuthenticationFilter filter = filter(INTERNAL_TOKEN);
        MockHttpServletRequest request = new MockHttpServletRequest("POST", "/internal/ai/auth/validate");
        MockHttpServletResponse response = new MockHttpServletResponse();
        MockFilterChain filterChain = new MockFilterChain();

        request.addHeader("Authorization", "Bearer " + INTERNAL_TOKEN);

        filter.doFilter(request, response, filterChain);

        assertThat(response.getStatus()).isEqualTo(200);
        assertThat(SecurityContextHolder.getContext().getAuthentication()).isNotNull();
        assertThat(SecurityContextHolder.getContext().getAuthentication().getPrincipal()).isEqualTo("AI_INTERNAL");
    }

    @Test
    void nonInternalPathDoesNotRequireInternalToken() throws Exception {
        AiInternalAuthenticationFilter filter = filter(INTERNAL_TOKEN);
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/api/v1/users/me");
        MockHttpServletResponse response = new MockHttpServletResponse();
        MockFilterChain filterChain = new MockFilterChain();

        filter.doFilter(request, response, filterChain);

        assertThat(response.getStatus()).isEqualTo(200);
        assertThat(SecurityContextHolder.getContext().getAuthentication()).isNull();
    }

    private AiInternalAuthenticationFilter filter(String internalToken) {
        AiInternalProperties properties = new AiInternalProperties();
        properties.setToken(internalToken);
        return new AiInternalAuthenticationFilter(properties, new ObjectMapper());
    }
}
