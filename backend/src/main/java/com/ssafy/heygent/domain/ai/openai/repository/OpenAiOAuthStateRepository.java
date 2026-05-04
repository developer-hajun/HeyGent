package com.ssafy.heygent.domain.ai.openai.repository;

import java.util.Optional;

import org.springframework.data.jpa.repository.JpaRepository;

import com.ssafy.heygent.domain.ai.openai.entity.OpenAiOAuthState;

public interface OpenAiOAuthStateRepository extends JpaRepository<OpenAiOAuthState, Long> {

    Optional<OpenAiOAuthState> findByState(String state);
}
