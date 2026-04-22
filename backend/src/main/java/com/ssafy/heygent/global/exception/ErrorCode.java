package com.ssafy.heygent.global.exception;

import lombok.Getter;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;

@Getter
@RequiredArgsConstructor
public enum ErrorCode {

    // 400 BAD_REQUEST
    // 예: 필수 요청값이 누락되었거나 형식이 잘못된 경우
    INVALID_REQUEST(HttpStatus.BAD_REQUEST, "잘못된 요청입니다."),
    INVALID_INPUT_VALUE(HttpStatus.BAD_REQUEST, "입력값이 올바르지 않습니다."),

    // 403 FORBIDDEN
    // 예: 로그인은 되었지만 해당 리소스에 접근 권한이 없는 경우
    ACCESS_DENIED(HttpStatus.FORBIDDEN, "접근 권한이 없습니다."),

    // 404 NOT_FOUND
    // 예: 요청한 ID에 해당하는 데이터가 존재하지 않는 경우
    RESOURCE_NOT_FOUND(HttpStatus.NOT_FOUND, "요청한 대상을 찾을 수 없습니다."),

    // 409 CONFLICT
    // 예: 이미 처리된 요청을 중복 수행하거나 현재 상태와 충돌하는 경우
    CONFLICT(HttpStatus.CONFLICT, "요청을 처리하는 중 충돌이 발생했습니다."),

    // 502 BAD_GATEWAY
    // 예: 외부 API 또는 AI 서버가 비정상 응답을 반환한 경우
    BAD_GATEWAY(HttpStatus.BAD_GATEWAY, "외부 서비스 처리 중 오류가 발생했습니다."),

    // 503 SERVICE_UNAVAILABLE
    // 예: 외부 서비스 타임아웃이나 일시적 장애가 발생한 경우
    SERVICE_UNAVAILABLE(HttpStatus.SERVICE_UNAVAILABLE, "서비스를 일시적으로 사용할 수 없습니다."),

    // 500 INTERNAL_SERVER_ERROR
    // 예: 예상하지 못한 서버 내부 예외가 발생한 경우
    INTERNAL_SERVER_ERROR(HttpStatus.INTERNAL_SERVER_ERROR, "서버 내부 오류가 발생했습니다.");

    private final HttpStatus status;
    private final String message;
}
