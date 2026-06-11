package com.ssafy.heygent.domain.ai.openai.service;

import java.util.regex.Matcher;
import java.util.regex.Pattern;

final class CodexDeviceAuthOutputParser {

    private static final Pattern ANSI_PATTERN = Pattern.compile("\\u001B\\[[;\\d]*m");
    private static final Pattern URL_PATTERN = Pattern.compile("https?://\\S+");
    private static final Pattern USER_CODE_PATTERN = Pattern.compile("\\b[A-Z0-9]{4,}-[A-Z0-9]{4,}\\b");

    private CodexDeviceAuthOutputParser() {
    }

    static ParsedDeviceAuthOutput parse(String output) {
        String normalized = stripAnsi(output == null ? "" : output);
        String verificationUri = null;
        String userCode = null;

        Matcher urlMatcher = URL_PATTERN.matcher(normalized);
        while (urlMatcher.find()) {
            String candidate = trimTrailingPunctuation(urlMatcher.group());
            if (verificationUri == null || candidate.contains("/codex/device")) {
                verificationUri = candidate;
            }
        }

        Matcher codeMatcher = USER_CODE_PATTERN.matcher(normalized);
        while (codeMatcher.find()) {
            userCode = codeMatcher.group();
        }

        return new ParsedDeviceAuthOutput(verificationUri, userCode);
    }

    private static String stripAnsi(String value) {
        return ANSI_PATTERN.matcher(value).replaceAll("");
    }

    private static String trimTrailingPunctuation(String value) {
        return value.replaceAll("[).,]+$", "");
    }

    record ParsedDeviceAuthOutput(String verificationUri, String userCode) {

        boolean isComplete() {
            return verificationUri != null && userCode != null;
        }
    }
}
