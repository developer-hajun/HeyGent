package com.ssafy.heygent.domain.ai.controller;

import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.ssafy.heygent.domain.ai.dto.request.OpenAiCredentialIssueRequest;
import com.ssafy.heygent.domain.ai.dto.response.OpenAiCredentialIssueResponse;
import com.ssafy.heygent.domain.ai.openai.service.OpenAiCredentialIssueService;
import com.ssafy.heygent.global.exception.ApiResponse;

import io.swagger.v3.oas.annotations.Operation;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;

@RestController
@RequiredArgsConstructor
@RequestMapping("/internal/ai/openai")
public class AiInternalOpenAiController {

    private final OpenAiCredentialIssueService openAiCredentialIssueService;

    @Operation(summary = "AI 서버용 OpenAI credential 발급", description = "AI 서버가 OpenAI 호출에 사용할 수 있는 사용자별 credential 정보를 발급합니다.")
    @PostMapping("/credentials/issue")
    public ApiResponse<OpenAiCredentialIssueResponse> issueCredential(
        @Valid @RequestBody OpenAiCredentialIssueRequest request
    ) {
        return ApiResponse.success(openAiCredentialIssueService.issue(request));
    }
}
