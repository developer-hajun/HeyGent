package com.ssafy.heygent.domain.notion.service;

import java.nio.charset.StandardCharsets;

import org.springframework.http.converter.StringHttpMessageConverter;
import org.springframework.web.client.RestTemplate;

final class Utf8RestTemplateFactory {

    private Utf8RestTemplateFactory() {
    }

    static RestTemplate create() {
        RestTemplate restTemplate = new RestTemplate();
        restTemplate.getMessageConverters().removeIf(StringHttpMessageConverter.class::isInstance);
        restTemplate.getMessageConverters().add(1, new StringHttpMessageConverter(StandardCharsets.UTF_8));
        return restTemplate;
    }
}
