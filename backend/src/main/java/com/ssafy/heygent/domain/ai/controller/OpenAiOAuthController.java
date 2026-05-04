package com.ssafy.heygent.domain.ai.controller;

import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import com.ssafy.heygent.domain.ai.dto.request.OpenAiOAuthStartRequest;
import com.ssafy.heygent.domain.ai.dto.response.OpenAiOAuthConnectionResponse;
import com.ssafy.heygent.domain.ai.dto.response.OpenAiOAuthStartResponse;
import com.ssafy.heygent.domain.ai.openai.service.OpenAiOAuthService;
import com.ssafy.heygent.global.config.security.CustomUserPrincipal;
import com.ssafy.heygent.global.exception.ApiResponse;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;

@RestController
@RequiredArgsConstructor
@RequestMapping("/api/v1/ai/openai/oauth")
public class OpenAiOAuthController {

    private final OpenAiOAuthService openAiOAuthService;

    @PostMapping("/start")
    public ApiResponse<OpenAiOAuthStartResponse> start(
        @AuthenticationPrincipal CustomUserPrincipal user,
        @Valid @RequestBody OpenAiOAuthStartRequest request
    ) {
        return ApiResponse.success(openAiOAuthService.start(resolveUserId(user), request));
    }

    @GetMapping(value = "/callback", produces = MediaType.TEXT_HTML_VALUE)
    public ResponseEntity<String> callback(
        @RequestParam String code,
        @RequestParam String state
    ) {
        OpenAiOAuthConnectionResponse response = openAiOAuthService.complete(code, state);
        return ResponseEntity.ok("""
            <html>
              <head><meta charset="utf-8" /></head>
              <body>
                <h1>OpenAI OAuth 연결 완료</h1>
                <p>status: %s</p>
                <p>expiresAt: %s</p>
              </body>
            </html>
            """.formatted(response.getStatus(), response.getExpiresAt()));
    }

    @PostMapping("/refresh")
    public ApiResponse<OpenAiOAuthConnectionResponse> refresh(
        @AuthenticationPrincipal CustomUserPrincipal user
    ) {
        return ApiResponse.success(openAiOAuthService.refresh(resolveUserId(user)));
    }

    @DeleteMapping
    public ApiResponse<OpenAiOAuthConnectionResponse> disconnect(
        @AuthenticationPrincipal CustomUserPrincipal user
    ) {
        return ApiResponse.success(openAiOAuthService.disconnect(resolveUserId(user)));
    }

    private Long resolveUserId(CustomUserPrincipal user) {
        if (user == null || user.getUserId() == null) {
            throw new CustomException(ErrorCode.INVALID_TOKEN);
        }
        return user.getUserId();
    }
}
