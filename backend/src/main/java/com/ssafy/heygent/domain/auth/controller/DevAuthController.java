package com.ssafy.heygent.domain.auth.controller;

import org.springframework.context.annotation.Profile;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import com.ssafy.heygent.domain.auth.dto.response.TokenResponse;
import com.ssafy.heygent.domain.auth.service.AuthService;
import com.ssafy.heygent.global.exception.ApiResponse;

import io.swagger.v3.oas.annotations.Operation;
import lombok.RequiredArgsConstructor;

@Profile("local")
@RestController
@RequiredArgsConstructor
@RequestMapping("/api/v1/auth")
public class DevAuthController {

    private final AuthService authService;

    @Operation(summary = "개발용 테스트 로그인", description = "local 프로필에서만 테스트 사용자로 토큰을 발급합니다.")
    @PostMapping("/dev-login")
    public ApiResponse<TokenResponse> devLogin(
            @RequestParam(required = false) String userKey
    ) {
        TokenResponse response = authService.devLogin(userKey);
        return ApiResponse.success(response);
    }
}
