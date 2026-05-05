package com.ssafy.heygent.domain.ai.controller;

import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import com.ssafy.heygent.domain.ai.dto.request.OpenAiCredentialIssueRequest;
import com.ssafy.heygent.domain.ai.dto.request.OpenAiResponsesRequest;
import com.ssafy.heygent.domain.ai.dto.response.OpenAiCredentialIssueResponse;
import com.ssafy.heygent.domain.ai.dto.response.OpenAiResponsesResponse;
import com.ssafy.heygent.domain.ai.openai.service.OpenAiCredentialIssueService;
import com.ssafy.heygent.domain.ai.service.AiInternalOpenAiService;
import com.ssafy.heygent.global.exception.ApiResponse;

import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;

@RestController
@RequiredArgsConstructor
@RequestMapping("/internal/ai/openai")
public class AiInternalOpenAiController {

    private final AiInternalOpenAiService aiInternalOpenAiService;
    private final OpenAiCredentialIssueService openAiCredentialIssueService;

    @PostMapping("/responses")
    public ApiResponse<OpenAiResponsesResponse> createResponse(
        @Valid @RequestBody OpenAiResponsesRequest request
    ) {
        return ApiResponse.success(aiInternalOpenAiService.createResponse(request));
    }

    @PostMapping("/credentials/issue")
    public ApiResponse<OpenAiCredentialIssueResponse> issueCredential(
        @Valid @RequestBody OpenAiCredentialIssueRequest request
    ) {
        return ApiResponse.success(openAiCredentialIssueService.issue(request));
    }
}
