package com.ssafy.heygent.domain.ai.openai.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

import com.ssafy.heygent.domain.ai.dto.request.OpenAiOAuthStartRequest;
import com.ssafy.heygent.domain.ai.dto.response.OpenAiOAuthStartResponse;
import com.ssafy.heygent.domain.ai.openai.config.OpenAiProperties;
import com.ssafy.heygent.domain.ai.openai.entity.OpenAiOAuthState;
import com.ssafy.heygent.domain.ai.openai.repository.OpenAiOAuthStateRepository;
import com.ssafy.heygent.domain.ai.openai.repository.OpenAiProviderConnectionRepository;
import com.ssafy.heygent.domain.ai.openai.security.OpenAiCredentialCipher;

@ExtendWith(MockitoExtension.class)
class OpenAiOAuthServiceTest {

    @Mock
    private OpenAiOAuthStateRepository openAiOAuthStateRepository;

    @Mock
    private OpenAiProviderConnectionRepository openAiProviderConnectionRepository;

    private OpenAiProperties properties;
    private OpenAiCredentialCipher credentialCipher;
    private OpenAiOAuthService openAiOAuthService;

    @BeforeEach
    void setUp() {
        properties = new OpenAiProperties();
        properties.setCredentialEncryptionKey("test-credential-encryption-key");
        properties.getOauth().setClientId("openai-client-id");
        properties.getOauth().setRedirectUri("http://localhost:8080/api/v1/ai/openai/oauth/callback");
        properties.getOauth().setScopes(List.of("openid", "profile", "offline_access"));

        credentialCipher = new OpenAiCredentialCipher(properties);
        openAiOAuthService = new OpenAiOAuthService(
            properties,
            openAiOAuthStateRepository,
            openAiProviderConnectionRepository,
            credentialCipher
        );
    }

    @Test
    void startSavesStateAndReturnsAuthorizationUrl() {
        OpenAiOAuthStartRequest request = new OpenAiOAuthStartRequest();
        ReflectionTestUtils.setField(request, "redirectUri", "http://localhost:8080/callback");
        when(openAiOAuthStateRepository.save(any(OpenAiOAuthState.class)))
            .thenAnswer(invocation -> invocation.getArgument(0));

        OpenAiOAuthStartResponse response = openAiOAuthService.start(1L, request);

        ArgumentCaptor<OpenAiOAuthState> stateCaptor = ArgumentCaptor.forClass(OpenAiOAuthState.class);
        verify(openAiOAuthStateRepository).save(stateCaptor.capture());

        OpenAiOAuthState savedState = stateCaptor.getValue();
        assertThat(savedState.getUserId()).isEqualTo(1L);
        assertThat(savedState.getRedirectUri()).isEqualTo("http://localhost:8080/callback");
        assertThat(credentialCipher.decrypt(savedState.getEncryptedCodeVerifier())).isNotBlank();
        assertThat(response.getStatus()).isEqualTo("authorization_required");
        assertThat(response.getState()).isEqualTo(savedState.getState());
        assertThat(response.getAuthorizationUrl()).contains("response_type=code");
        assertThat(response.getAuthorizationUrl()).contains("client_id=openai-client-id");
        assertThat(response.getAuthorizationUrl()).contains("code_challenge_method=S256");
    }
}
