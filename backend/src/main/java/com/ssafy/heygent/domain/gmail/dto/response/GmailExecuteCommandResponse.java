package com.ssafy.heygent.domain.gmail.dto.response;

import lombok.Getter;

@Getter
public class GmailExecuteCommandResponse {

    private final int index;
    private final Long userId;
    private final String method;
    private final String endpoint;
    private final boolean success;
    private final Object data;
    private final String errorCode;
    private final String errorMessage;

    private GmailExecuteCommandResponse(
        int index,
        Long userId,
        String method,
        String endpoint,
        boolean success,
        Object data,
        String errorCode,
        String errorMessage
    ) {
        this.index = index;
        this.userId = userId;
        this.method = method;
        this.endpoint = endpoint;
        this.success = success;
        this.data = data;
        this.errorCode = errorCode;
        this.errorMessage = errorMessage;
    }

    public static GmailExecuteCommandResponse success(
        int index,
        Long userId,
        String method,
        String endpoint,
        Object data
    ) {
        return new GmailExecuteCommandResponse(
            index,
            userId,
            method,
            endpoint,
            true,
            data,
            null,
            null
        );
    }

    public static GmailExecuteCommandResponse failure(
        int index,
        Long userId,
        String method,
        String endpoint,
        String errorCode,
        String errorMessage
    ) {
        return new GmailExecuteCommandResponse(
            index,
            userId,
            method,
            endpoint,
            false,
            null,
            errorCode,
            errorMessage
        );
    }
}
