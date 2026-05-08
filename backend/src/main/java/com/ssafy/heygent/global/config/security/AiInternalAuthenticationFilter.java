package com.ssafy.heygent.global.config.security;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Collections;

import org.springframework.http.MediaType;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;
import org.springframework.web.filter.OncePerRequestFilter;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.ssafy.heygent.global.exception.ErrorCode;
import com.ssafy.heygent.global.exception.ErrorResponse;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;

@Component
@RequiredArgsConstructor
public class AiInternalAuthenticationFilter extends OncePerRequestFilter {

    private static final String INTERNAL_AI_PATH_PREFIX = "/internal/ai/";
    private static final String BEARER_PREFIX = "Bearer ";
    private static final String AI_INTERNAL_PRINCIPAL = "AI_INTERNAL";

    private final AiInternalProperties aiInternalProperties;
    private final ObjectMapper objectMapper;

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        return !request.getRequestURI().startsWith(INTERNAL_AI_PATH_PREFIX);
    }

    @Override
    protected void doFilterInternal(
        HttpServletRequest request,
        HttpServletResponse response,
        FilterChain filterChain
    ) throws ServletException, IOException {
        String token = resolveBearerToken(request);

        if (!isValidInternalToken(token)) {
            writeErrorResponse(response);
            return;
        }

        UsernamePasswordAuthenticationToken authentication = new UsernamePasswordAuthenticationToken(
            AI_INTERNAL_PRINCIPAL,
            null,
            Collections.emptyList()
        );
        SecurityContextHolder.getContext().setAuthentication(authentication);
        filterChain.doFilter(request, response);
    }

    private String resolveBearerToken(HttpServletRequest request) {
        String authorization = request.getHeader("Authorization");
        if (authorization != null && authorization.startsWith(BEARER_PREFIX)) {
            return authorization.substring(BEARER_PREFIX.length());
        }
        return null;
    }

    private boolean isValidInternalToken(String token) {
        String configuredToken = aiInternalProperties.getToken();
        if (!StringUtils.hasText(token) || !StringUtils.hasText(configuredToken)) {
            return false;
        }
        return MessageDigest.isEqual(
            token.getBytes(StandardCharsets.UTF_8),
            configuredToken.getBytes(StandardCharsets.UTF_8)
        );
    }

    private void writeErrorResponse(HttpServletResponse response) throws IOException {
        ErrorCode errorCode = ErrorCode.INVALID_TOKEN;
        ErrorResponse errorResponse = ErrorResponse.builder()
            .status(errorCode.getStatus().value())
            .error(errorCode.getStatus().name())
            .code(errorCode.name())
            .message(errorCode.getMessage())
            .build();

        response.setStatus(errorCode.getStatus().value());
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        response.setCharacterEncoding(StandardCharsets.UTF_8.name());
        objectMapper.writeValue(response.getWriter(), errorResponse);
    }
}
