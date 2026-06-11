package com.ssafy.heygent.domain.auth.controller;

import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.ssafy.heygent.domain.auth.dto.request.KakaoLoginRequest;
import com.ssafy.heygent.domain.auth.dto.request.KakaoMobileLoginRequest;
import com.ssafy.heygent.domain.auth.dto.response.TokenResponse;
import com.ssafy.heygent.domain.auth.service.AuthService;
import com.ssafy.heygent.global.exception.ApiResponse;

import io.swagger.v3.oas.annotations.Operation;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;

@RestController
@RequiredArgsConstructor
@RequestMapping("/api/v1/auth")
public class AuthController {

    private final AuthService authService;

    @Operation(summary = "카카오 로그인", description = "인가 코드를 받아 카카오 소셜 로그인을 진행하고 JWT 토큰을 발급합니다.")
    @PostMapping("/kakao")
    public ApiResponse<TokenResponse> kakaoLogin(
            @Valid @RequestBody KakaoLoginRequest request
    ) {
        TokenResponse response = authService.kakaoLogin(request.getCode());
        return ApiResponse.success(response);
    }


    @Operation(summary = "카카오 모바일 로그인", description = "카카오 액세스 토큰을 받아 소셜 로그인을 진행하고 JWT 토큰을 발급합니다.")
    @PostMapping("/kakao/mobile")
    public ApiResponse<TokenResponse> kakaoMobileLogin(
            @Valid @RequestBody KakaoMobileLoginRequest request
    ) {
        TokenResponse response = authService.kakaoMobileLogin(request.getAccessToken());
        return ApiResponse.success(response);
    }

    @Operation(summary = "로그아웃", description = "Refresh Token을 기반으로 로그아웃 처리합니다.")
    @PostMapping("/logout")
    public ApiResponse<Void> logout(
            @RequestHeader("Refresh-Token") String refreshToken
    ) {
        authService.logout(refreshToken);
        return ApiResponse.success("로그아웃 되었습니다.", null);
    }

    @Operation(summary = "토큰 재발급", description = "Refresh Token을 이용하여 Access Token을 재발급합니다.")
    @PostMapping("/refresh")
    public ApiResponse<TokenResponse> refresh(
            @RequestHeader("Refresh-Token") String refreshToken
    ) {
        TokenResponse response = authService.refresh(refreshToken);
        return ApiResponse.success(response);
    }

}
