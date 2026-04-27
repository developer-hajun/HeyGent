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

# 비루트 유저로 실행
RUN groupadd --system app && useradd --system --gid app app
COPY --from=build --chown=app:app /workspace/build/libs/*.jar /app/app.jar

USER app
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "/app/app.jar"]
