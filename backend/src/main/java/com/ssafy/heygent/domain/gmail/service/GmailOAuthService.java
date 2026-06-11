package com.ssafy.heygent.domain.gmail.service;

import org.springframework.stereotype.Service;

import com.ssafy.heygent.domain.gmail.dto.response.GmailConnectUrlResponse;
import com.ssafy.heygent.domain.gmail.dto.response.GmailStatusResponse;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
public class GmailOAuthService {

    private final GmailComposioService gmailComposioService;

    public GmailConnectUrlResponse getConnectUrl(Long userId) {
        String url = gmailComposioService.getGmailConnectUrl(userId);
        return new GmailConnectUrlResponse(url);
    }

    public GmailStatusResponse getStatus(Long userId) {
        boolean connected = gmailComposioService.isGmailConnected(userId);
        return new GmailStatusResponse(connected);
    }

    public void disconnect(Long userId) {
        gmailComposioService.disconnectGmail(userId);
    }
}
