package com.ssafy.heygent.global.exception;

import jakarta.servlet.http.HttpServletRequest;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@Slf4j
@RestControllerAdvice
public class GlobalExceptionHandler {

    // 우리가 만든 CustomException 발생 시 처리
    @ExceptionHandler(CustomException.class)
    protected org.springframework.http.ResponseEntity<ErrorResponse> handleCustomException(CustomException e) {
        log.error("handleCustomException throw CustomException : {}", e.getErrorCode());
        return ErrorResponse.toResponseEntity(e.getErrorCode());
    }

    // @Valid 유효성 검사 에러 처리
    @ExceptionHandler(MethodArgumentNotValidException.class)
    protected org.springframework.http.ResponseEntity<ErrorResponse> handleValidationException(
        MethodArgumentNotValidException e,
        HttpServletRequest request
    ) {
        log.error("Validation Error - url: {}, message: {}", request.getRequestURI(), e.getMessage());

        // 첫 번째 에러 메시지 추출 로직
        String errorMessage = e.getBindingResult().getFieldErrors().stream()
            .findFirst()
            .map(FieldError::getDefaultMessage)
            .orElse(ErrorCode.INVALID_INPUT_VALUE.getMessage());

        // ErrorResponse 형태에 맞춰서 직접 조립해서 반환
        return org.springframework.http.ResponseEntity
            .status(ErrorCode.INVALID_INPUT_VALUE.getStatus())
            .body(ErrorResponse.builder()
                .status(ErrorCode.INVALID_INPUT_VALUE.getStatus().value())
                .error(ErrorCode.INVALID_INPUT_VALUE.getStatus().name())
                .code(ErrorCode.INVALID_INPUT_VALUE.name())
                .message(errorMessage)
                .build());
    }

    // 잘못된 JSON 문법이나 DTO 역직렬화 실패는 마지막 Exception 핸들러로 보내면 500이 될 수 있어서,
    // 입력 형식 오류로 분리해 400 BAD_REQUEST로 고정 처리한다.
    @ExceptionHandler(HttpMessageNotReadableException.class)
    protected org.springframework.http.ResponseEntity<ErrorResponse> handleHttpMessageNotReadableException(
        HttpMessageNotReadableException exception,
        HttpServletRequest request
    ) {
        log.error("Message Not Readable - url: {}, message: {}", request.getRequestURI(), exception.getMessage());
        return ErrorResponse.toResponseEntity(ErrorCode.INVALID_REQUEST);
    }

    // 그 외에 예상치 못한 모든 Exception 발생 시 처리 (500 에러)
    @ExceptionHandler(Exception.class)
    protected org.springframework.http.ResponseEntity<ErrorResponse> handleException(Exception e) {
        log.error("handleException throw Exception : {}", e.getMessage());
        return ErrorResponse.toResponseEntity(ErrorCode.INTERNAL_SERVER_ERROR);
    }
}
