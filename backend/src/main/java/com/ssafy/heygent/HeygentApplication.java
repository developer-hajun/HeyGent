package com.ssafy.heygent;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.data.jpa.repository.config.EnableJpaAuditing;

@SpringBootApplication
@EnableJpaAuditing
public class HeygentApplication {

	public static void main(String[] args) {
		SpringApplication.run(HeygentApplication.class, args);
	}

}
