package com.ssafy.heygent.global.exception;

import lombok.Getter;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;

@Getter
@RequiredArgsConstructor
public enum ErrorCode {

    // 400 BAD_REQUEST
    INVALID_REQUEST(HttpStatus.BAD_REQUEST, "잘못된 요청입니다."),
    INVALID_INPUT_VALUE(HttpStatus.BAD_REQUEST, "입력값이 올바르지 않습니다."),
    OPENAI_PROVIDER_NOT_SUPPORTED(HttpStatus.BAD_REQUEST, "지원하지 않는 OpenAI Provider입니다."),
    OPENAI_MODEL_NOT_ALLOWED(HttpStatus.BAD_REQUEST, "허용되지 않은 OpenAI 모델입니다."),
    OPENAI_OAUTH_STATE_INVALID(HttpStatus.BAD_REQUEST, "OpenAI OAuth state가 유효하지 않습니다."),

    // 401 UNAUTHORIZED
    INVALID_TOKEN(HttpStatus.UNAUTHORIZED, "유효하지 않은 토큰입니다."),

    // 403 FORBIDDEN
    ACCESS_DENIED(HttpStatus.FORBIDDEN, "접근 권한이 없습니다."),

    // 404 NOT_FOUND
    RESOURCE_NOT_FOUND(HttpStatus.NOT_FOUND, "요청한 대상을 찾을 수 없습니다."),

    // 409 CONFLICT
    CONFLICT(HttpStatus.CONFLICT, "요청을 처리하는 중 충돌이 발생했습니다."),
    DEVICE_INACTIVE(HttpStatus.CONFLICT, "비활성화된 IoT 디바이스입니다."),

    // 502 BAD_GATEWAY
    EXTERNAL_AUTH_FAILED(HttpStatus.BAD_GATEWAY, "외부 인증 처리 중 오류가 발생했습니다."),
    BAD_GATEWAY(HttpStatus.BAD_GATEWAY, "외부 서비스 처리 중 오류가 발생했습니다."),
    OPENAI_CALL_FAILED(HttpStatus.BAD_GATEWAY, "OpenAI 호출 처리 중 오류가 발생했습니다."),
    OPENAI_OAUTH_TOKEN_EXCHANGE_FAILED(HttpStatus.BAD_GATEWAY, "OpenAI OAuth token 교환 중 오류가 발생했습니다."),

    // 503 SERVICE_UNAVAILABLE
    SERVICE_UNAVAILABLE(HttpStatus.SERVICE_UNAVAILABLE, "서비스를 일시적으로 사용할 수 없습니다."),
    OPENAI_PROVIDER_NOT_CONFIGURED(HttpStatus.SERVICE_UNAVAILABLE, "OpenAI Provider 설정이 완료되지 않았습니다."),
    OPENAI_OAUTH_NOT_CONNECTED(HttpStatus.SERVICE_UNAVAILABLE, "OpenAI OAuth 연결이 필요합니다."),

    // 500 INTERNAL_SERVER_ERROR
    INTERNAL_SERVER_ERROR(HttpStatus.INTERNAL_SERVER_ERROR, "서버 내부 오류가 발생했습니다.");

    private final HttpStatus status;
    private final String message;
}
