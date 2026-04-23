package com.ssafy.heygent.domain.user.controller;

import com.ssafy.heygent.domain.user.dto.request.UpdateMyInfoRequest;
import com.ssafy.heygent.domain.user.entity.User;
import com.ssafy.heygent.domain.user.repository.UserRepository;
import com.ssafy.heygent.global.config.security.CustomUserPrincipal;
import com.ssafy.heygent.global.exception.ApiResponse;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;
import io.swagger.v3.oas.annotations.Operation;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.util.StringUtils;
import org.springframework.web.bind.annotation.*;
import jakarta.validation.Valid;

@RestController
@RequiredArgsConstructor
@RequestMapping("/api/v1/users")
public class UserController {

    private final UserRepository userRepository;

    @Operation(summary = "내 정보 조회", description = "JWT 기반으로 로그인된 사용자 정보를 조회합니다.")
    @GetMapping("/me")
    public ApiResponse<User> getMyInfo(@AuthenticationPrincipal CustomUserPrincipal user) {

        Long userId = user.getUserId();

        User findUser = userRepository.findById(userId)
                .orElseThrow(() -> new CustomException(ErrorCode.RESOURCE_NOT_FOUND));

        return ApiResponse.success(findUser);
    }

    @Operation(summary = "내 정보 수정", description = "로그인된 사용자의 닉네임과 프로필 이미지를 부분 수정합니다.")
    @PatchMapping("/me")
    public ApiResponse<User> updateMyInfo(
            @AuthenticationPrincipal CustomUserPrincipal user,
            @Valid @RequestBody UpdateMyInfoRequest request
    ) {

        if (!StringUtils.hasText(request.getNickname()) && !StringUtils.hasText(request.getProfileImage())) {
            throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
        }

        Long userId = user.getUserId();

        User findUser = userRepository.findById(userId)
                .orElseThrow(() -> new CustomException(ErrorCode.RESOURCE_NOT_FOUND));

        String nickname = StringUtils.hasText(request.getNickname()) ? request.getNickname().trim() : null;
        String profileImage = StringUtils.hasText(request.getProfileImage()) ? request.getProfileImage().trim() : null;

        findUser.updateProfile(nickname, profileImage);
        User updatedUser = userRepository.save(findUser);

        return ApiResponse.success(updatedUser);
    }
}
