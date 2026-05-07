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

import com.ssafy.heygent.domain.ai.dto.request.OpenAiCodexOAuthCompleteRequest;
import com.ssafy.heygent.domain.ai.dto.response.OpenAiCodexOAuthStatusResponse;
import com.ssafy.heygent.domain.ai.dto.response.OpenAiOAuthConnectionResponse;
import com.ssafy.heygent.domain.ai.dto.response.OpenAiOAuthStartResponse;
import com.ssafy.heygent.domain.ai.openai.service.OpenAiCodexOAuthService;
import com.ssafy.heygent.global.config.security.CustomUserPrincipal;
import com.ssafy.heygent.global.exception.ApiResponse;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

import io.swagger.v3.oas.annotations.Operation;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;

@RestController
@RequiredArgsConstructor
@RequestMapping("/api/v1/ai/codex/oauth")
public class OpenAiCodexOAuthController {

    private final OpenAiCodexOAuthService openAiCodexOAuthService;

    @Operation(summary = "Codex OAuth 연결 시작", description = "로그인된 사용자의 Codex OAuth 연결을 시작하고 인증 URL을 반환합니다.")
    @PostMapping("/start")
    public ApiResponse<OpenAiOAuthStartResponse> start(
        @AuthenticationPrincipal CustomUserPrincipal user
    ) {
        return ApiResponse.success(openAiCodexOAuthService.start(resolveUserId(user)));
    }

    @Operation(summary = "Codex OAuth 콜백", description = "Codex OAuth 인증 완료 후 전달된 code와 state를 처리하고 연결 결과 HTML을 반환합니다.")
    @GetMapping(value = "/callback", produces = MediaType.TEXT_HTML_VALUE)
    public ResponseEntity<String> callback(
        @RequestParam String code,
        @RequestParam String state
    ) {
        OpenAiOAuthConnectionResponse response = openAiCodexOAuthService.complete(code, state);
        return ResponseEntity.ok("""
            <html>
              <head><meta charset="utf-8" /></head>
              <body>
                <h1>Codex OAuth 연결 완료</h1>
                <p>status: %s</p>
                <p>expiresAt: %s</p>
              </body>
            </html>
            """.formatted(response.getStatus(), response.getExpiresAt()));
    }

    @Operation(
        summary = "Codex OAuth 연결 완료",
        description = "로컬 콜백 캡처가 실패했을 때 사용자가 붙여넣은 redirect URL 또는 code/state로 Codex OAuth 연결을 완료합니다."
    )
    @PostMapping("/complete")
    public ApiResponse<OpenAiOAuthConnectionResponse> complete(
        @Valid @RequestBody OpenAiCodexOAuthCompleteRequest request
    ) {
        return ApiResponse.success(openAiCodexOAuthService.complete(request));
    }

    @Operation(summary = "Codex OAuth 상태 조회", description = "로그인된 사용자의 Codex OAuth 연결 상태를 조회합니다.")
    @GetMapping("/status")
    public ApiResponse<OpenAiCodexOAuthStatusResponse> status(
        @AuthenticationPrincipal CustomUserPrincipal user
    ) {
        return ApiResponse.success(openAiCodexOAuthService.getStatus(resolveUserId(user)));
    }

    @Operation(summary = "Codex OAuth 토큰 갱신", description = "로그인된 사용자의 Codex OAuth 토큰을 갱신하고 연결 상태를 반환합니다.")
    @PostMapping("/refresh")
    public ApiResponse<OpenAiOAuthConnectionResponse> refresh(
        @AuthenticationPrincipal CustomUserPrincipal user
    ) {
        return ApiResponse.success(openAiCodexOAuthService.refresh(resolveUserId(user)));
    }

    @Operation(summary = "Codex OAuth 연결 해제", description = "로그인된 사용자의 Codex OAuth 연결을 해제하고 변경된 연결 상태를 반환합니다.")
    @DeleteMapping
    public ApiResponse<OpenAiOAuthConnectionResponse> disconnect(
        @AuthenticationPrincipal CustomUserPrincipal user
    ) {
        return ApiResponse.success(openAiCodexOAuthService.disconnect(resolveUserId(user)));
    }

    private Long resolveUserId(CustomUserPrincipal user) {
        if (user == null || user.getUserId() == null) {
            throw new CustomException(ErrorCode.INVALID_TOKEN);
        }
        return user.getUserId();
    }
}
