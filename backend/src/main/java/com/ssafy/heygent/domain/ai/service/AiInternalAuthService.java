package com.ssafy.heygent.domain.ai.service;

import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.Date;
import java.util.List;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.StringUtils;

import com.ssafy.heygent.domain.ai.dto.request.AiAuthValidateRequest;
import com.ssafy.heygent.domain.ai.dto.response.AiAuthValidateResponse;
import com.ssafy.heygent.domain.user.repository.UserRepository;
import com.ssafy.heygent.domain.workspace.service.WorkspaceAccessService;
import com.ssafy.heygent.global.config.jwt.JwtProvider;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

import lombok.RequiredArgsConstructor;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class AiInternalAuthService {

    private static final List<String> DEFAULT_AI_SCOPE = List.of("AI_TASK_RUN");
    private static final int DEFAULT_SCOPE_TTL_MINUTES = 10;

    private final JwtProvider jwtProvider;
    private final UserRepository userRepository;
    private final WorkspaceAccessService workspaceAccessService;

    public AiAuthValidateResponse validate(AiAuthValidateRequest request) {
        String accessToken = request.getAccessToken().trim();
        if (!jwtProvider.validateToken(accessToken)) {
            throw new CustomException(ErrorCode.INVALID_TOKEN);
        }

        Long userId = jwtProvider.getUserId(accessToken);
        if (!userRepository.existsById(userId)) {
            throw new CustomException(ErrorCode.INVALID_TOKEN);
        }

        LocalDateTime jwtExpiresAt = toLocalDateTime(jwtProvider.getExpiration(accessToken));
        LocalDateTime verifiedAt = LocalDateTime.now();
        String workspaceKey = resolveWorkspaceKey(userId, request.getWorkspaceKey());

        return AiAuthValidateResponse.builder()
            .userId(userId)
            .workspaceKey(workspaceKey)
            .scope(DEFAULT_AI_SCOPE)
            .jwtExpiresAt(jwtExpiresAt)
            .scopeExpiresAt(verifiedAt.plusMinutes(DEFAULT_SCOPE_TTL_MINUTES))
            .build();
    }

    private String resolveWorkspaceKey(Long userId, String workspaceKey) {
        if (!StringUtils.hasText(workspaceKey)) {
            return null;
        }
        return workspaceAccessService.validateAccess(userId, workspaceKey);
    }

    private LocalDateTime toLocalDateTime(Date date) {
        return LocalDateTime.ofInstant(date.toInstant(), ZoneId.systemDefault());
    }
}
