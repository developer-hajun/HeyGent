package com.ssafy.heygent.domain.auth.dto.request;

import jakarta.validation.constraints.NotBlank;
import lombok.Getter;

@Getter
public class KakaoLoginRequest {

    @NotBlank(message = "인가 코드는 필수입니다.")
    private String code;
}
