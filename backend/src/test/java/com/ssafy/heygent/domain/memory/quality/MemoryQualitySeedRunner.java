package com.ssafy.heygent.domain.memory.quality;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.time.LocalDateTime;
import java.util.Locale;

public class MemoryQualitySeedRunner {

    private static final String DEFAULT_DATASOURCE_URL = "jdbc:postgresql://127.0.0.1:5432/heygent";
    private static final int DEFAULT_USER_COUNT = 100;
    private static final int DEFAULT_MEMORIES_PER_USER = 100;
    private static final int DEFAULT_HEAVY_USER_MEMORIES = 1000;
    private static final long BASE_USER_ID = 900_000L;
    private static final long HEAVY_USER_ID = BASE_USER_ID + 999L;

    public static void main(String[] args) throws SQLException {
        String datasourceUrl = env("SPRING_DATASOURCE_URL", DEFAULT_DATASOURCE_URL);
        String username = requiredEnv("SPRING_DATASOURCE_USERNAME");
        String password = requiredEnv("SPRING_DATASOURCE_PASSWORD");
        int userCount = envInt("MEMORY_QUALITY_USERS", DEFAULT_USER_COUNT);
        int memoriesPerUser = envInt("MEMORY_QUALITY_MEMORIES_PER_USER", DEFAULT_MEMORIES_PER_USER);
        int heavyUserMemories = envInt("MEMORY_QUALITY_HEAVY_USER_MEMORIES", DEFAULT_HEAVY_USER_MEMORIES);
        boolean cleanup = envBoolean("MEMORY_QUALITY_CLEANUP", false);

        try (Connection connection = DriverManager.getConnection(datasourceUrl, username, password)) {
            connection.setAutoCommit(false);
            if (cleanup) {
                deleteSeedMemories(connection);
                connection.commit();
                System.out.printf("Deleted quality seed memories. userId >= %d%n", BASE_USER_ID);
                return;
            }

            int inserted = seedMemories(connection, userCount, memoriesPerUser, heavyUserMemories);
            connection.commit();
            System.out.printf(
                "Inserted %d quality seed memories. users=%d, memoriesPerUser=%d, heavyUserMemories=%d%n",
                inserted,
                userCount,
                memoriesPerUser,
                heavyUserMemories
            );
            System.out.printf("Heavy user id for recall test: %d%n", HEAVY_USER_ID);
        }
    }

    private static int seedMemories(
        Connection connection,
        int userCount,
        int memoriesPerUser,
        int heavyUserMemories
    ) throws SQLException {
        deleteSeedMemories(connection);
        int inserted = 0;

        try (PreparedStatement statement = connection.prepareStatement("""
            INSERT INTO user_memories (
                user_id,
                store_type,
                memory_type,
                scope_type,
                content,
                summary,
                metadata,
                embedding_text,
                importance,
                confidence,
                status,
                source_session_key,
                evidence,
                valid_from,
                expires_at,
                access_count,
                used_count,
                usefulness_score
            )
            VALUES (?, ?, ?, ?, ?, ?, CAST(? AS jsonb), ?, ?, ?, 'ACTIVE', ?, ?, ?, ?, 0, 0, 0.0)
            """)) {
            for (int userIndex = 0; userIndex < userCount; userIndex++) {
                long userId = BASE_USER_ID + userIndex;
                inserted += insertUserMemories(statement, userId, memoriesPerUser);
            }
            inserted += insertUserMemories(statement, HEAVY_USER_ID, heavyUserMemories);
        }

        return inserted;
    }

    private static int insertUserMemories(
        PreparedStatement statement,
        long userId,
        int memoryCount
    ) throws SQLException {
        int inserted = 0;

        for (int index = 0; index < memoryCount; index++) {
            MemorySeed seed = createSeed(userId, index);
            statement.setLong(1, userId);
            statement.setString(2, seed.storeType());
            statement.setString(3, seed.memoryType());
            statement.setString(4, seed.scopeType());
            statement.setString(5, seed.content());
            statement.setString(6, seed.summary());
            statement.setString(7, seed.metadata());
            statement.setString(8, seed.embeddingText());
            statement.setDouble(9, seed.importance());
            statement.setDouble(10, seed.confidence());
            statement.setString(11, seed.sourceSessionKey());
            statement.setString(12, seed.evidence());
            statement.setTimestamp(13, Timestamp.valueOf(seed.validFrom()));
            if (seed.expiresAt() == null) {
                statement.setTimestamp(14, null);
            } else {
                statement.setTimestamp(14, Timestamp.valueOf(seed.expiresAt()));
            }
            statement.addBatch();
            inserted++;

            if (inserted % 500 == 0) {
                statement.executeBatch();
            }
        }
        statement.executeBatch();
        return inserted;
    }

    private static MemorySeed createSeed(long userId, int index) {
        String memoryType = switch (index % 5) {
            case 0 -> "PREFERENCE";
            case 1 -> "PROFILE";
            case 2 -> "INSTRUCTION";
            case 3 -> "PROCEDURE";
            default -> "FACT";
        };
        String storeType = ("PREFERENCE".equals(memoryType) || "PROFILE".equals(memoryType))
            ? "USER_PROFILE"
            : "AGENT_MEMORY";
        String scopeType = switch (index % 4) {
            case 0 -> "GLOBAL";
            case 1 -> "WORKSPACE";
            case 2 -> "RESOURCE";
            default -> "SESSION";
        };
        String topic = topic(index);
        String content = "quality-seed user " + userId + " memory " + index + " about " + topic;
        String summary = topic + " seed memory " + index;
        String workspaceKey = "workspace-" + (index % 10);
        String resourceId = "resource-" + (index % 25);
        String sessionKey = "session-" + userId + "-" + (index % 20);
        String metadata = metadata(scopeType, workspaceKey, resourceId, sessionKey, topic);
        String sourceSessionKey = "SESSION".equals(scopeType) ? sessionKey : null;
        LocalDateTime now = LocalDateTime.now();
        LocalDateTime expiresAt = "SESSION".equals(scopeType) ? now.plusDays(1) : null;
        double importance = 0.55 + ((index % 40) / 100.0);
        double confidence = 0.7 + ((index % 30) / 100.0);

        return new MemorySeed(
            storeType,
            memoryType,
            scopeType,
            content,
            summary,
            metadata,
            embedding(index),
            importance,
            confidence,
            sourceSessionKey,
            "quality seed evidence " + index,
            now.minusDays(index % 30),
            expiresAt
        );
    }

    private static String topic(int index) {
        return switch (index % 8) {
            case 0 -> "short practical answers";
            case 1 -> "frontend framework choice";
            case 2 -> "backend api specification";
            case 3 -> "meeting summary format";
            case 4 -> "source citation style";
            case 5 -> "debugging workflow";
            case 6 -> "portfolio writing";
            default -> "deployment checklist";
        };
    }

    private static String metadata(
        String scopeType,
        String workspaceKey,
        String resourceId,
        String sessionKey,
        String topic
    ) {
        String base = "\"source\":\"quality-seed\",\"tags\":[\"quality\",\"%s\"]".formatted(slug(topic));
        return switch (scopeType) {
            case "WORKSPACE" -> "{%s,\"workspaceKey\":\"%s\"}".formatted(base, workspaceKey);
            case "RESOURCE" -> "{%s,\"resourceId\":\"%s\"}".formatted(base, resourceId);
            case "SESSION" -> "{%s,\"sessionKey\":\"%s\"}".formatted(base, sessionKey);
            default -> "{%s}".formatted(base);
        };
    }

    private static String embedding(int index) {
        double first = ((index % 100) + 1) / 100.0;
        double second = 1.0 - first;
        return "[%f,%f]".formatted(Locale.ROOT, first, second);
    }

    private static void deleteSeedMemories(Connection connection) throws SQLException {
        try (PreparedStatement statement = connection.prepareStatement("""
            DELETE FROM user_memories
            WHERE user_id >= ?
                AND metadata ->> 'source' = 'quality-seed'
            """)) {
            statement.setLong(1, BASE_USER_ID);
            statement.executeUpdate();
        }
    }

    private static String env(String key, String defaultValue) {
        String value = System.getenv(key);
        if (value == null || value.isBlank()) {
            return defaultValue;
        }
        return value;
    }

    private static String requiredEnv(String key) {
        String value = System.getenv(key);
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException(key + " environment variable is required.");
        }
        return value;
    }

    private static int envInt(String key, int defaultValue) {
        String value = System.getenv(key);
        if (value == null || value.isBlank()) {
            return defaultValue;
        }
        return Integer.parseInt(value);
    }

    private static boolean envBoolean(String key, boolean defaultValue) {
        String value = System.getenv(key);
        if (value == null || value.isBlank()) {
            return defaultValue;
        }
        return Boolean.parseBoolean(value);
    }

    private static String slug(String value) {
        return value.toLowerCase(Locale.ROOT).replace(" ", "-");
    }

    private record MemorySeed(
        String storeType,
        String memoryType,
        String scopeType,
        String content,
        String summary,
        String metadata,
        String embeddingText,
        double importance,
        double confidence,
        String sourceSessionKey,
        String evidence,
        LocalDateTime validFrom,
        LocalDateTime expiresAt
    ) {
    }
}
