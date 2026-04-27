package com.ssafy.heygent.domain.memory.repository;

import java.sql.PreparedStatement;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.StringJoiner;

import org.springframework.dao.DataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;
import org.springframework.util.StringUtils;

import com.ssafy.heygent.domain.memory.embedding.MemoryEmbeddingService;
import com.ssafy.heygent.domain.memory.entity.MemoryScopeType;
import com.ssafy.heygent.domain.memory.entity.MemoryStatus;
import com.ssafy.heygent.domain.memory.entity.MemoryStoreType;
import com.ssafy.heygent.domain.memory.entity.MemoryType;

import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;

@Slf4j
@Repository
@RequiredArgsConstructor
public class UserMemoryVectorRepository {

    private final JdbcTemplate jdbcTemplate;
    private final MemoryEmbeddingService memoryEmbeddingService;
    private boolean pgvectorAvailable;

    @PostConstruct
    public void initializeVectorColumn() {
        initializeMemoryTypeConstraint();

        jdbcTemplate.execute("""
            ALTER TABLE user_memories
            ADD COLUMN IF NOT EXISTS embedding_text TEXT
            """);

        try {
            jdbcTemplate.execute("CREATE EXTENSION IF NOT EXISTS vector");
            jdbcTemplate.execute("""
                ALTER TABLE user_memories
                ADD COLUMN IF NOT EXISTS embedding vector(%d)
                """.formatted(memoryEmbeddingService.getDimensions()));
            jdbcTemplate.execute("""
                CREATE INDEX IF NOT EXISTS idx_user_memories_embedding
                ON user_memories
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
                """);
            pgvectorAvailable = true;
        } catch (DataAccessException exception) {
            pgvectorAvailable = false;
            log.warn(
                "pgvector is unavailable. User memories use embedding_text fallback. reason={}",
                exception.getMostSpecificCause().getMessage()
            );
        }
    }

    private void initializeMemoryTypeConstraint() {
        jdbcTemplate.execute("""
            ALTER TABLE user_memories
            DROP CONSTRAINT IF EXISTS user_memories_memory_type_check
            """);
        jdbcTemplate.execute("""
            ALTER TABLE user_memories
            ADD CONSTRAINT user_memories_memory_type_check
            CHECK (memory_type IN (
                'PREFERENCE',
                'PROFILE',
                'CONTEXT',
                'PROJECT_CONTEXT',
                'INSTRUCTION',
                'PROCEDURE',
                'FACT'
            ))
            """);
    }

    public void updateEmbedding(Long memoryId, List<Double> embedding) {
        String vectorLiteral = toVectorLiteral(embedding);
        jdbcTemplate.update(
            "UPDATE user_memories SET embedding_text = ? WHERE id = ?",
            vectorLiteral,
            memoryId
        );

        if (!pgvectorAvailable) {
            return;
        }

        try {
            jdbcTemplate.update(
                "UPDATE user_memories SET embedding = CAST(? AS vector) WHERE id = ?",
                vectorLiteral,
                memoryId
            );
        } catch (DataAccessException exception) {
            log.warn(
                "Failed to update pgvector memory embedding. memoryId={}, reason={}",
                memoryId,
                exception.getMostSpecificCause().getMessage()
            );
        }
    }

    public List<Long> searchIds(
        Long userId,
        List<Double> queryEmbedding,
        MemoryStoreType storeType,
        MemoryType memoryType,
        MemoryScopeType scopeType,
        String workspaceKey,
        String sessionKey,
        String resourceId,
        List<String> tags,
        double minConfidence,
        double minImportance,
        int limit
    ) {
        if (!pgvectorAvailable) {
            return List.of();
        }

        List<Object> params = new ArrayList<>();
        StringBuilder sql = new StringBuilder("""
            SELECT id
            FROM user_memories
            WHERE user_id = ?
                AND status = ?
                AND confidence >= ?
                AND importance >= ?
                AND embedding IS NOT NULL
                AND (valid_from IS NULL OR valid_from <= now())
                AND (valid_until IS NULL OR valid_until > now())
                AND (expires_at IS NULL OR expires_at > now())
            """);

        params.add(userId);
        params.add(MemoryStatus.ACTIVE.name());
        params.add(minConfidence);
        params.add(minImportance);

        appendEnumFilter(sql, params, "store_type", storeType);
        appendEnumFilter(sql, params, "memory_type", memoryType);
        appendEnumFilter(sql, params, "scope_type", scopeType);
        appendDefaultSessionExclusion(sql, scopeType);
        appendMetadataFilter(sql, params, "workspaceKey", workspaceKey);
        appendMetadataFilter(sql, params, "sessionKey", sessionKey);
        appendMetadataFilter(sql, params, "resourceId", resourceId);
        appendTagsFilter(sql, params, tags);

        sql.append("""
            ORDER BY embedding <=> CAST(? AS vector), importance DESC, confidence DESC
            LIMIT ?
            """);
        params.add(toVectorLiteral(queryEmbedding));
        params.add(limit);

        try {
            return jdbcTemplate.query(
                connection -> {
                    PreparedStatement statement = connection.prepareStatement(sql.toString());
                    for (int i = 0; i < params.size(); i++) {
                        statement.setObject(i + 1, params.get(i));
                    }
                    return statement;
                },
                (rs, rowNum) -> rs.getLong("id")
            );
        } catch (DataAccessException exception) {
            log.warn(
                "Failed to search user memories by pgvector. userId={}, reason={}",
                userId,
                exception.getMostSpecificCause().getMessage()
            );
            return List.of();
        }
    }

    private void appendEnumFilter(StringBuilder sql, List<Object> params, String column, Enum<?> value) {
        if (value == null) {
            return;
        }
        sql.append(" AND ").append(column).append(" = ?");
        params.add(value.name());
    }

    private void appendDefaultSessionExclusion(StringBuilder sql, MemoryScopeType scopeType) {
        if (scopeType != null) {
            return;
        }
        sql.append(" AND (scope_type IS NULL OR scope_type <> 'SESSION')");
    }

    private void appendMetadataFilter(StringBuilder sql, List<Object> params, String key, String value) {
        if (!StringUtils.hasText(value)) {
            return;
        }
        sql.append(" AND metadata ->> ? = ?");
        params.add(key);
        params.add(value.trim());
    }

    private void appendTagsFilter(StringBuilder sql, List<Object> params, List<String> tags) {
        List<String> normalizedTags = tags == null ? List.of() : tags.stream()
            .filter(StringUtils::hasText)
            .map(String::trim)
            .filter(Objects::nonNull)
            .toList();

        if (normalizedTags.isEmpty()) {
            return;
        }

        sql.append(" AND (");
        StringJoiner joiner = new StringJoiner(" OR ");
        normalizedTags.forEach(tag -> {
            joiner.add("jsonb_exists(metadata -> 'tags', ?)");
            params.add(tag);
        });
        sql.append(joiner);
        sql.append(")");
    }

    private String toVectorLiteral(List<Double> embedding) {
        StringJoiner joiner = new StringJoiner(",", "[", "]");
        embedding.forEach(value -> joiner.add(value.toString()));
        return joiner.toString();
    }
}
