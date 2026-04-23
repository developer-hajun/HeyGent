package com.ssafy.heygent.domain.auth.oauth;

import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor
public class KakaoUserInfo {

    private Long kakaoId;
    private String nickname;
    private String profileImage;
}
