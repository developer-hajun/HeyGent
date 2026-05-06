package com.ssafy.heygent.domain.ai.service;

import org.springframework.stereotype.Service;

import com.ssafy.heygent.domain.ai.dto.request.OpenAiResponsesRequest;
import com.ssafy.heygent.domain.ai.dto.response.OpenAiResponsesResponse;
import com.ssafy.heygent.domain.ai.openai.dto.OpenAiResponsesCommand;
import com.ssafy.heygent.domain.ai.openai.dto.OpenAiResponsesResult;
import com.ssafy.heygent.domain.ai.openai.service.OpenAiProviderService;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
public class AiInternalOpenAiService {

    private final OpenAiProviderService openAiProviderService;

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
        return OpenAiResponsesResponse.from(result);
    }
}
