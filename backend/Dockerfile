# syntax=docker/dockerfile:1.6

# ===== Build stage =====
FROM eclipse-temurin:21-jdk-jammy AS build
WORKDIR /workspace

# 1) gradle wrapper / 빌드 설정만 먼저 복사 (의존성 변경 없을 때 캐시 재사용)
COPY gradlew ./
COPY gradle ./gradle
COPY build.gradle settings.gradle ./
COPY checkstyle ./checkstyle
RUN chmod +x gradlew

# 2) 소스 복사 후 jar 빌드 (test, checkstyle 제외 - 이미지 빌드 단계에선 스킵)
#    BuildKit cache mount 으로 gradle home(~/.gradle)을 호스트에 캐시 → 재빌드 시 의존성 재다운로드 회피
COPY src ./src
RUN --mount=type=cache,target=/root/.gradle \
    ./gradlew bootJar --no-daemon -x test -x checkstyleMain -x checkstyleTest

# ===== Runtime stage =====
FROM eclipse-temurin:21-jre-jammy
WORKDIR /app

# Codex device OAuth 용 Node.js 20 + @openai/codex CLI 설치
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates \
 && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
 && apt-get install -y --no-install-recommends nodejs \
 && npm install -g @openai/codex \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# 비루트 유저로 실행
RUN groupadd --system app && useradd --system --gid app app
COPY --from=build --chown=app:app /workspace/build/libs/*.jar /app/app.jar

# Codex device OAuth 작업 폴더 (app 유저 소유, 본인만 접근)
RUN mkdir -p /tmp/heygent-codex-device-oauth \
 && chown app:app /tmp/heygent-codex-device-oauth \
 && chmod 700 /tmp/heygent-codex-device-oauth

USER app
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
