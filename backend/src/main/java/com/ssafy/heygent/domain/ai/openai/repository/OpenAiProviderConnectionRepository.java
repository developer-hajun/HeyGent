package com.ssafy.heygent.domain.ai.openai.repository;

import java.util.Optional;

import org.springframework.data.jpa.repository.JpaRepository;

import com.ssafy.heygent.domain.ai.openai.entity.OpenAiProviderConnection;

public interface OpenAiProviderConnectionRepository extends JpaRepository<OpenAiProviderConnection, Long> {

    Optional<OpenAiProviderConnection> findByUserIdAndProviderName(Long userId, String providerName);

    void deleteByUserIdAndProviderName(Long userId, String providerName);
}
