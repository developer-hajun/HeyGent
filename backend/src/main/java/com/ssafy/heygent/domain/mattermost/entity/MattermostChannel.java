package com.ssafy.heygent.domain.mattermost.entity;

import java.time.LocalDateTime;

import org.springframework.data.annotation.CreatedDate;
import org.springframework.data.annotation.LastModifiedDate;
import org.springframework.data.jpa.domain.support.AuditingEntityListener;

import com.ssafy.heygent.domain.user.entity.User;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EntityListeners;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Index;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
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
        name = "mattermost_channels",
        uniqueConstraints = {
                @UniqueConstraint(name = "uk_mattermost_channels_user_alias", columnNames = {"user_id", "alias"})
        },
        indexes = {
                @Index(name = "idx_mattermost_channels_user_id", columnList = "user_id"),
                @Index(name = "idx_mattermost_channels_user_default", columnList = "user_id,is_default")
        }
)
@EntityListeners(AuditingEntityListener.class)
public class MattermostChannel {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @Column(nullable = false, length = 40)
    private String alias;

    @Column(name = "display_name", nullable = false, length = 60)
    private String displayName;

    @Column(name = "webhook_url", nullable = false, length = 512)
    private String webhookUrl;

    @Column(name = "is_default", nullable = false)
    private boolean defaultChannel;

    @CreatedDate
    @Column(updatable = false)
    private LocalDateTime createdAt;

    @LastModifiedDate
    private LocalDateTime updatedAt;

    public void update(String alias, String displayName, String webhookUrl) {
        this.alias = alias;
        this.displayName = displayName;
        if (webhookUrl != null && !webhookUrl.isBlank()) {
            this.webhookUrl = webhookUrl;
        }
    }

    public void markDefault(boolean defaultChannel) {
        this.defaultChannel = defaultChannel;
    }
}
