package com.ssafy.heygent.domain.ai.controller;

import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import com.ssafy.heygent.domain.ai.dto.response.OpenAiOAuthConnectionResponse;
import com.ssafy.heygent.domain.ai.openai.service.OpenAiCodexOAuthService;

import io.swagger.v3.oas.annotations.Operation;
import lombok.RequiredArgsConstructor;

@RestController
@RequiredArgsConstructor
@RequestMapping("/auth")
public class OpenAiCodexOAuthLocalCallbackController {

    private final OpenAiCodexOAuthService openAiCodexOAuthService;

    @Operation(summary = "Codex OAuth 로컬 콜백", description = "Codex public client의 localhost 콜백을 처리합니다.")
    @GetMapping(value = "/callback", produces = MediaType.TEXT_HTML_VALUE)
    public ResponseEntity<String> callback(
        @RequestParam String code,
        @RequestParam String state
    ) {
        OpenAiOAuthConnectionResponse response = openAiCodexOAuthService.complete(code, state);
        return ResponseEntity.ok("""
            <html>
              <head><meta charset="utf-8" /></head>
              <body>
                <h1>Codex OAuth 연결 완료</h1>
                <p>status: %s</p>
                <p>expiresAt: %s</p>
              </body>
            </html>
            """.formatted(response.getStatus(), response.getExpiresAt()));
    }
}
