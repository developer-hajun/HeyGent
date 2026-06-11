package com.ssafy.heygent.domain.auth.dto.request;

import jakarta.validation.constraints.NotBlank;
import lombok.Getter;

@Getter
public class KakaoMobileLoginRequest {

    @NotBlank(message = "카카오 액세스 토큰은 필수입니다.")
    private String accessToken;
}
