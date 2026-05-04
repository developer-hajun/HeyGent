package com.ssafy.heygent.domain.notion.service;

import org.springframework.stereotype.Service;

import com.ssafy.heygent.domain.notion.dto.response.NotionConnectUrlResponse;
import com.ssafy.heygent.domain.notion.dto.response.NotionStatusResponse;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
public class NotionOAuthService {

    private final ComposioService composioService;

    public NotionConnectUrlResponse getConnectUrl(Long userId) {
        String url = composioService.getNotionConnectUrl(userId);
        return new NotionConnectUrlResponse(url);
    }

    public NotionStatusResponse getStatus(Long userId) {
        boolean connected = composioService.isNotionConnected(userId);
        return new NotionStatusResponse(connected);
    }

    public void disconnect(Long userId) {
        composioService.disconnectNotion(userId);
    }
}
