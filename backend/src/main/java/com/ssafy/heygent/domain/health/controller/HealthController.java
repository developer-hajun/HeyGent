package com.ssafy.heygent.domain.health.controller;

import com.ssafy.heygent.domain.health.dto.request.SamsungHealthRequestDto;
import com.ssafy.heygent.domain.health.dto.response.HealthSummaryResponseDto;
import com.ssafy.heygent.domain.health.service.HealthService;
import com.ssafy.heygent.global.config.jwt.JwtProvider;
import com.ssafy.heygent.global.config.security.CustomUserPrincipal;
import com.ssafy.heygent.global.exception.ApiResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/health")
@RequiredArgsConstructor
public class HealthController {

    private final HealthService healthService; // 비즈니스 로직 처리를 위한 서비스
    private final JwtProvider jwtProvider;

    @GetMapping("/me/latest")
    public ApiResponse<HealthSummaryResponseDto> getLatestHealthData(
            @AuthenticationPrincipal CustomUserPrincipal user) {
        return healthService.getLatestHealthData(user.getUserId())
                .map(ApiResponse::success)
                .orElseGet(ApiResponse::success);
    }

    @PostMapping("/samsung")
    public ApiResponse<String> saveSamsungHealthData(
            @AuthenticationPrincipal CustomUserPrincipal user,
            @RequestBody SamsungHealthRequestDto requestDto) {
        Long userId = user.getUserId();
        healthService.processHealthData(userId, requestDto);
        return ApiResponse.success();
    }
}