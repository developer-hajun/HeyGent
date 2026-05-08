package com.ssafy.heygent.domain.notion.dto.response;

import lombok.Getter;

@Getter
public class NotionExecuteCommandResponse {

    private final int index;
    private final Long userId;
    private final String method;
    private final String endpoint;
    private final String notionVersion;
    private final boolean success;
    private final Object data;
    private final String errorCode;
    private final String errorMessage;

    private NotionExecuteCommandResponse(
        int index,
        Long userId,
        String method,
        String endpoint,
        String notionVersion,
        boolean success,
        Object data,
        String errorCode,
        String errorMessage
    ) {
        this.index = index;
        this.userId = userId;
        this.method = method;
        this.endpoint = endpoint;
        this.notionVersion = notionVersion;
        this.success = success;
        this.data = data;
        this.errorCode = errorCode;
        this.errorMessage = errorMessage;
    }

    public static NotionExecuteCommandResponse success(
        int index,
        Long userId,
        String method,
        String endpoint,
        String notionVersion,
        Object data
    ) {
        return new NotionExecuteCommandResponse(
            index,
            userId,
            method,
            endpoint,
            notionVersion,
            true,
            data,
            null,
            null
        );
    }

    public static NotionExecuteCommandResponse failure(
        int index,
        Long userId,
        String method,
        String endpoint,
        String notionVersion,
        String errorCode,
        String errorMessage
    ) {
        return new NotionExecuteCommandResponse(
            index,
            userId,
            method,
            endpoint,
            notionVersion,
            false,
            null,
            errorCode,
            errorMessage
        );
    }
}
