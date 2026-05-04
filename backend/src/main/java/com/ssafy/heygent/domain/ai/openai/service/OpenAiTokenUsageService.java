package com.ssafy.heygent.domain.ai.openai.service;

import java.util.Map;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.ssafy.heygent.domain.ai.openai.dto.OpenAiResponsesCommand;
import com.ssafy.heygent.domain.ai.openai.dto.OpenAiResponsesResult;
import com.ssafy.heygent.domain.ai.openai.dto.OpenAiUsage;
import com.ssafy.heygent.domain.ai.openai.entity.AiTokenUsageLog;
import com.ssafy.heygent.domain.ai.openai.repository.AiTokenUsageLogRepository;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
public class OpenAiTokenUsageService {

    private final AiTokenUsageLogRepository aiTokenUsageLogRepository;

    @Transactional
    public AiTokenUsageLog record(OpenAiResponsesCommand command, OpenAiResponsesResult result) {
        OpenAiUsage usage = result.usage() == null ? OpenAiUsage.empty() : result.usage();
        AiTokenUsageLog usageLog = AiTokenUsageLog.builder()
            .userId(command.userId())
            .taskRunId(command.taskRunId())
            .stepRunId(command.stepRunId())
            .providerName(result.providerName())
            .authType(result.authType())
            .model(result.model())
            .responseId(result.responseId())
            .inputTokens(usage.inputTokens())
            .cachedInputTokens(usage.cachedInputTokens())
            .outputTokens(usage.outputTokens())
            .reasoningTokens(usage.reasoningTokens())
            .totalTokens(usage.totalTokens())
            .rawUsage(rawUsage(result))
            .metadata(command.metadata() == null ? Map.of() : command.metadata())
            .build();

        return aiTokenUsageLogRepository.save(usageLog);
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> rawUsage(OpenAiResponsesResult result) {
        if (result.rawResponse() == null || !(result.rawResponse().get("usage") instanceof Map<?, ?> usage)) {
            return Map.of();
        }
        return (Map<String, Object>)usage;
    }
}
