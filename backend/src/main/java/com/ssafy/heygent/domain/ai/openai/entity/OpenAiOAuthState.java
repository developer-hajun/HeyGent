package com.ssafy.heygent.domain.ai.openai.entity;

import java.time.LocalDateTime;

import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.jpa.domain.support.AuditingEntityListener;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EntityListeners;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Index;
import jakarta.persistence.Table;
import lombok.AccessLevel;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Entity
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor
@Builder
@Table(
    name = "openai_oauth_states",
    indexes = {
        @Index(name = "idx_openai_oauth_states_state", columnList = "state", unique = true),
        @Index(name = "idx_openai_oauth_states_user_created", columnList = "user_id, created_at")
    }
)
@EntityListeners(AuditingEntityListener.class)
public class OpenAiOAuthState {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true, length = 120)
    private String state;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(name = "redirect_uri", nullable = false, length = 500)
    private String redirectUri;

    @Column(name = "encrypted_code_verifier", nullable = false, length = 1000)
    private String encryptedCodeVerifier;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 30)
    private OpenAiOAuthStateStatus status;

    @Column(name = "expires_at", nullable = false)
    private LocalDateTime expiresAt;

    @CreatedDate
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;

    @Column(name = "consumed_at")
    private LocalDateTime consumedAt;

    public boolean isPending(LocalDateTime now) {
        return status == OpenAiOAuthStateStatus.PENDING && expiresAt.isAfter(now);
    }

    public void consume(LocalDateTime consumedAt) {
        this.status = OpenAiOAuthStateStatus.CONSUMED;
        this.consumedAt = consumedAt;
    }
}
