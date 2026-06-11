package com.ssafy.heygent.domain.iot.config;

import org.eclipse.paho.client.mqttv3.MqttConnectOptions;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.integration.annotation.ServiceActivator;
import org.springframework.integration.channel.DirectChannel;
import org.springframework.integration.mqtt.core.DefaultMqttPahoClientFactory;
import org.springframework.integration.mqtt.core.MqttPahoClientFactory;
import org.springframework.integration.mqtt.outbound.MqttPahoMessageHandler;
import org.springframework.messaging.MessageChannel;
import org.springframework.messaging.MessageHandler;
import org.springframework.util.StringUtils;

@Configuration
@EnableConfigurationProperties(MqttProperties.class)
public class MqttConfig {

    @Bean
    @ConditionalOnProperty(prefix = "iot.mqtt", name = "enabled", havingValue = "true")
    public MqttPahoClientFactory mqttClientFactory(MqttProperties properties) {
        MqttConnectOptions options = new MqttConnectOptions();
        options.setServerURIs(new String[] {properties.brokerUri()});
        options.setCleanSession(true);
        options.setAutomaticReconnect(true);
        options.setConnectionTimeout(properties.getConnectionTimeoutSeconds());

        if (StringUtils.hasText(properties.getUsername())) {
            options.setUserName(properties.getUsername());
        }
        if (StringUtils.hasText(properties.getPassword())) {
            options.setPassword(properties.getPassword().toCharArray());
        }

        DefaultMqttPahoClientFactory clientFactory = new DefaultMqttPahoClientFactory();
        clientFactory.setConnectionOptions(options);
        return clientFactory;
    }

    @Bean
    @ConditionalOnProperty(prefix = "iot.mqtt", name = "enabled", havingValue = "true")
    public MessageChannel mqttOutboundChannel() {
        return new DirectChannel();
    }

    @Bean
    @ServiceActivator(inputChannel = "mqttOutboundChannel")
    @ConditionalOnProperty(prefix = "iot.mqtt", name = "enabled", havingValue = "true")
    public MessageHandler mqttOutboundHandler(
        MqttPahoClientFactory mqttClientFactory,
        MqttProperties properties
    ) {
        MqttPahoMessageHandler handler = new MqttPahoMessageHandler(properties.getClientId(), mqttClientFactory);
        handler.setAsync(false);
        handler.setDefaultQos(normalizeQos(properties.getDefaultQos()));
        handler.setDefaultTopic(defaultTopic(properties));
        handler.setCompletionTimeout(properties.getPublishTimeoutSeconds() * 1000L);
        return handler;
    }

    private int normalizeQos(int qos) {
        return Math.max(0, Math.min(2, qos));
    }

    private String defaultTopic(MqttProperties properties) {
        if (StringUtils.hasText(properties.getTopicPrefix())) {
            return properties.getTopicPrefix();
        }
        return "devices";
    }
}
