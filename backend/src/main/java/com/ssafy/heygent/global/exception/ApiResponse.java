package com.ssafy.heygent.global.exception;

import com.fasterxml.jackson.annotation.JsonInclude;
import lombok.AccessLevel;
import lombok.AllArgsConstructor;
import lombok.Getter;

@Getter
@AllArgsConstructor(access = AccessLevel.PRIVATE)
@JsonInclude(JsonInclude.Include.NON_NULL) // null인 필드는 JSON 응답에서 제외
public class ApiResponse<T> {

    private final int status;
    private final String message;
    private final T data;

    // 1. 성공 응답 (데이터가 있는 경우)
    public static <T> ApiResponse<T> success(T data) {
        return new ApiResponse<>(200, "요청에 성공했습니다.", data);
    }

    // 2. 성공 응답 (커스텀 메시지 + 데이터)
    public static <T> ApiResponse<T> success(String message, T data) {
        return new ApiResponse<>(200, message, data);
    }

    // 3. 성공 응답 (데이터가 없는 경우 - Create, Delete 등에 사용)
    public static <T> ApiResponse<T> success() {
        return new ApiResponse<>(200, "요청에 성공했습니다.", null);
    }
}
