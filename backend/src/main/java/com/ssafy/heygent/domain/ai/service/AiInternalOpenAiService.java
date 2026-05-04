package com.ssafy.heygent.domain.ai.service;

import org.springframework.stereotype.Service;

import com.ssafy.heygent.domain.ai.dto.request.OpenAiResponsesRequest;
import com.ssafy.heygent.domain.ai.dto.response.OpenAiResponsesResponse;
import com.ssafy.heygent.domain.ai.openai.dto.OpenAiResponsesCommand;
import com.ssafy.heygent.domain.ai.openai.dto.OpenAiResponsesResult;
import com.ssafy.heygent.domain.ai.openai.service.OpenAiProviderService;
import com.ssafy.heygent.domain.ai.openai.service.OpenAiTokenUsageService;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
public class AiInternalOpenAiService {

    private final OpenAiProviderService openAiProviderService;
    private final OpenAiTokenUsageService openAiTokenUsageService;

    public OpenAiResponsesResponse createResponse(OpenAiResponsesRequest request) {
        OpenAiResponsesCommand command = new OpenAiResponsesCommand(
            request.getUserId(),
            request.getTaskRunId(),
            request.getStepRunId(),
            request.getProviderName(),
            request.getModel(),
            request.getInput(),
            request.getTools(),
            request.getToolChoice(),
            request.getMetadata()
        );
        OpenAiResponsesResult result = openAiProviderService.createResponse(command);
        openAiTokenUsageService.record(command, result);
        return OpenAiResponsesResponse.from(result);
    }
}
