package com.ssafy.heygent.domain.ai.openai.security;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import org.junit.jupiter.api.Test;

import com.ssafy.heygent.domain.ai.openai.config.OpenAiProperties;
import com.ssafy.heygent.global.exception.CustomException;
import com.ssafy.heygent.global.exception.ErrorCode;

class OpenAiCredentialCipherTest {

    @Test
    void encryptAndDecryptCredential() {
        OpenAiProperties properties = new OpenAiProperties();
        properties.setCredentialEncryptionKey("test-credential-encryption-key");
        OpenAiCredentialCipher cipher = new OpenAiCredentialCipher(properties);

        String encrypted = cipher.encrypt("openai-refresh-token");
        String decrypted = cipher.decrypt(encrypted);

        assertThat(encrypted).isNotEqualTo("openai-refresh-token");
        assertThat(decrypted).isEqualTo("openai-refresh-token");
    }

    @Test
    void encryptFailsWhenEncryptionKeyIsMissing() {
        OpenAiCredentialCipher cipher = new OpenAiCredentialCipher(new OpenAiProperties());

        assertThatThrownBy(() -> cipher.encrypt("openai-refresh-token"))
            .isInstanceOf(CustomException.class)
            .extracting("errorCode")
            .isEqualTo(ErrorCode.OPENAI_PROVIDER_NOT_CONFIGURED);
    }
}
