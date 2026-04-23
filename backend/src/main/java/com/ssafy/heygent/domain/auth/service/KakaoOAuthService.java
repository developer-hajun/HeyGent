package com.ssafy.heygent.domain.auth.oauth;

import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;

import java.util.Map;

@Service
public class KakaoOAuthService {

    @Value("${kakao.client-id}")
    private String clientId;

    @Value("${kakao.redirect-uri}")
    private String redirectUri;

    @Value("${kakao.client-secret}")
    private String clientSecret;

    public String getAccessToken(String code) {

        RestTemplate restTemplate = new RestTemplate();

        MultiValueMap<String, String> params = new LinkedMultiValueMap<>();
        params.add("grant_type", "authorization_code");
        params.add("client_id", clientId);
        params.add("redirect_uri", redirectUri);
        params.add("client_secret", clientSecret);
        params.add("code", code);

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_FORM_URLENCODED);

        HttpEntity<?> request = new HttpEntity<>(params, headers);

        try {
            ResponseEntity<Map> response = restTemplate.postForEntity(
                    "https://kauth.kakao.com/oauth/token",
                    request,
                    Map.class
            );

            Map<String, Object> body = response.getBody();
            if (body == null || body.get("access_token") == null) {
                throw new CustomException(ErrorCode.EXTERNAL_AUTH_FAILED);
            }

            return body.get("access_token").toString();
        } catch (RestClientException e) {
            throw new CustomException(ErrorCode.EXTERNAL_AUTH_FAILED);
        }
    }

    public KakaoUserInfo getUserInfo(String accessToken) {

        RestTemplate restTemplate = new RestTemplate();

        HttpHeaders headers = new HttpHeaders();
        headers.setBearerAuth(accessToken);

        HttpEntity<?> request = new HttpEntity<>(headers);

        try {
            ResponseEntity<Map> response = restTemplate.exchange(
                    "https://kapi.kakao.com/v2/user/me",
                    HttpMethod.GET,
                    request,
                    Map.class
            );

            Map<String, Object> body = response.getBody();
            if (body == null || body.get("id") == null) {
                throw new CustomException(ErrorCode.EXTERNAL_AUTH_FAILED);
            }

            Map<String, Object> properties = (Map<String, Object>) body.get("properties");
            if (properties == null) {
                throw new CustomException(ErrorCode.EXTERNAL_AUTH_FAILED);
            }

            return new KakaoUserInfo(
                    Long.valueOf(body.get("id").toString()),
                    (String) properties.get("nickname"),
                    (String) properties.get("profile_image")
            );
        } catch (RestClientException e) {
            throw new CustomException(ErrorCode.EXTERNAL_AUTH_FAILED);
        }
    }
}
