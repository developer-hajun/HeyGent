package com.ssafy.heygent.domain.iot.config;

import lombok.Getter;
import lombok.Setter;
import org.springframework.boot.context.properties.ConfigurationProperties;

@Getter
@Setter
@ConfigurationProperties(prefix = "iot.mqtt")
public class MqttProperties {

    private boolean enabled = false;
    private String host = "localhost";
    private int port = 1883;
    private String username = "";
    private String password = "";
    private String clientId = "heygent-backend";
    private int connectionTimeoutSeconds = 5;
    private int publishTimeoutSeconds = 3;
    private int defaultQos = 0;
    private String topicPrefix = "devices";

    public String brokerUri() {
        return "tcp://" + host + ":" + port;
    }
}
