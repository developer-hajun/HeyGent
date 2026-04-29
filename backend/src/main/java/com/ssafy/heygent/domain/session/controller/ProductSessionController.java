package com.ssafy.heygent.domain.session.controller;

import java.util.List;

import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.ssafy.heygent.domain.session.dto.request.CreateProductSessionRequest;
import com.ssafy.heygent.domain.session.dto.response.ProductSessionResponse;
import com.ssafy.heygent.domain.session.service.ProductSessionService;
import com.ssafy.heygent.global.config.security.CustomUserPrincipal;
import com.ssafy.heygent.global.exception.ApiResponse;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

import io.swagger.v3.oas.annotations.Operation;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;

@RestController
@RequiredArgsConstructor
@RequestMapping("/api/v1/sessions")
public class ProductSessionController {

    private final ProductSessionService productSessionService;

    @Operation(summary = "AI 작업 세션 생성", description = "로그인된 사용자 기준으로 AI 작업에서 참조할 product session을 생성합니다.")
    @PostMapping
    public ApiResponse<ProductSessionResponse> createSession(
        @AuthenticationPrincipal CustomUserPrincipal user,
        @Valid @RequestBody CreateProductSessionRequest request
    ) {
        return ApiResponse.success(productSessionService.create(resolveUserId(user), request));
    }

    @Operation(summary = "내 AI 작업 세션 목록 조회", description = "로그인된 사용자의 product session 목록을 조회합니다.")
    @GetMapping
    public ApiResponse<List<ProductSessionResponse>> getMySessions(
        @AuthenticationPrincipal CustomUserPrincipal user
    ) {
        return ApiResponse.success(productSessionService.getMySessions(resolveUserId(user)));
    }

    @Operation(summary = "AI 작업 세션 단건 조회", description = "로그인된 사용자가 소유한 product session을 조회합니다.")
    @GetMapping("/{sessionId}")
    public ApiResponse<ProductSessionResponse> getSession(
        @AuthenticationPrincipal CustomUserPrincipal user,
        @PathVariable Long sessionId
    ) {
        return ApiResponse.success(productSessionService.getSession(resolveUserId(user), sessionId));
    }

    private Long resolveUserId(CustomUserPrincipal user) {
        if (user == null || user.getUserId() == null) {
            throw new CustomException(ErrorCode.INVALID_TOKEN);
        }
        return user.getUserId();
    }
}
