package com.ssafy.heygent.domain.memory.service;

import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.regex.Pattern;

import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;

import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

@Component
public class MemorySafetyValidator {

    private static final int MAX_METADATA_KEYS = 20;
    private static final int MAX_METADATA_VALUE_LENGTH = 300;
    private static final int MAX_METADATA_TAGS = 20;
    private static final int MAX_METADATA_TAG_LENGTH = 50;

    private static final Set<String> ALLOWED_METADATA_KEYS = Set.of(
        "tags",
        "workspaceKey",
        "sessionKey",
        "resourceType",
        "resourceId",
        "source",
        "category"
    );

    private static final List<Pattern> BLOCKED_PATTERNS = List.of(
        Pattern.compile("(?i)ignore\\s+(all\\s+)?(previous|prior|above)\\s+(instructions|rules)"),
        Pattern.compile("(?i)disregard\\s+(all\\s+)?(previous|prior|above)\\s+(instructions|rules)"),
        Pattern.compile("(?i)(system|developer)\\s+(prompt|message|instruction)"),
        Pattern.compile("(?i)(reveal|print|dump|show|exfiltrate).{0,40}(secret|token|credential|api[_-]?key|password)"),
        Pattern.compile("(?i)(read|open|print|dump).{0,40}(\\.env|credentials|secrets?)"),
        Pattern.compile("(?i)(api[_-]?key|access[_-]?token|refresh[_-]?token|password)\\s*[:=]\\s*\\S+"),
        Pattern.compile("[\\u200B-\\u200F\\u202A-\\u202E\\u2060-\\u206F]")
    );

    public void validate(String content, String summary, Map<String, Object> metadata) {
        validateText(content);
        validateText(summary);
        validateMetadata(metadata);
    }

    private void validateText(String value) {
        if (!StringUtils.hasText(value)) {
            return;
        }

        for (Pattern pattern : BLOCKED_PATTERNS) {
            if (pattern.matcher(value).find()) {
                throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
            }
        }
    }

    private void validateMetadata(Map<String, Object> metadata) {
        if (metadata == null || metadata.isEmpty()) {
            return;
        }
        if (metadata.size() > MAX_METADATA_KEYS) {
            throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
        }

        for (Map.Entry<String, Object> entry : metadata.entrySet()) {
            if (!ALLOWED_METADATA_KEYS.contains(entry.getKey())) {
                throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
            }
            validateMetadataValue(entry.getKey(), entry.getValue());
        }
    }

    private void validateMetadataValue(String key, Object value) {
        if (value == null) {
            return;
        }
        if ("tags".equals(key)) {
            validateTags(value);
            return;
        }
        if (value instanceof Map<?, ?>) {
            throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
        }
        if (value instanceof List<?>) {
            throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
        }

        String textValue = value.toString();
        if (textValue.length() > MAX_METADATA_VALUE_LENGTH) {
            throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
        }
        validateText(textValue);
    }

    private void validateTags(Object value) {
        if (!(value instanceof List<?> tags)) {
            throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
        }
        if (tags.size() > MAX_METADATA_TAGS) {
            throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
        }

        tags.stream()
            .filter(Objects::nonNull)
            .map(Object::toString)
            .forEach(this::validateTag);
    }

    private void validateTag(String tag) {
        if (!StringUtils.hasText(tag) || tag.length() > MAX_METADATA_TAG_LENGTH) {
            throw new CustomException(ErrorCode.INVALID_INPUT_VALUE);
        }
        validateText(tag);
    }
}
