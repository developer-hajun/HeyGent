package com.ssafy.heygent.domain.ai.openai.entity;

import java.time.LocalDateTime;
import java.util.Map;

import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;
import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.jpa.domain.support.AuditingEntityListener;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EntityListeners;
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
    name = "openai_provider_connections",
    indexes = {
        @Index(name = "idx_openai_provider_connections_user_provider", columnList = "user_id, provider_name", unique = true)
    }
)
@EntityListeners(AuditingEntityListener.class)
public class OpenAiProviderConnection {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(name = "provider_name", nullable = false, length = 50)
    private String providerName;

    @Column(name = "token_type", length = 30)
    private String tokenType;

    @Column(name = "encrypted_access_token", nullable = false, length = 30000)
    private String encryptedAccessToken;

    @Column(name = "encrypted_refresh_token", length = 30000)
    private String encryptedRefreshToken;

    @Column(name = "scope_text", nullable = false, length = 500)
    private String scopeText;

    @Column(name = "expires_at")
    private LocalDateTime expiresAt;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition = "jsonb")
    private Map<String, Object> metadata;

    @CreatedDate
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;

    @LastModifiedDate
    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    public boolean isExpired(LocalDateTime now) {
        return expiresAt != null && !expiresAt.isAfter(now);
    }

    public void updateToken(
        String tokenType,
        String encryptedAccessToken,
        String encryptedRefreshToken,
        String scopeText,
        LocalDateTime expiresAt,
        Map<String, Object> metadata
    ) {
        this.tokenType = tokenType;
        this.encryptedAccessToken = encryptedAccessToken;
        this.encryptedRefreshToken = encryptedRefreshToken;
        this.scopeText = scopeText;
        this.expiresAt = expiresAt;
        this.metadata = metadata;
    }
}
