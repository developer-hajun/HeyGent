package com.ssafy.heygent.domain.user.dto.request;

import jakarta.validation.constraints.Size;
import lombok.Getter;

@Getter
public class UpdateMyInfoRequest {

    @Size(max = 100, message = "닉네임은 100자 이하여야 합니다.")
    private String nickname;

    @Size(max = 255, message = "프로필 이미지 URL은 255자 이하여야 합니다.")
    private String profileImage;
}
