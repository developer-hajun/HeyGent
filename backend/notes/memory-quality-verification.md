# 장기기억 검증 및 품질 테스트 기준

## 목적

장기기억 기능이 사용자 수와 기억 수가 늘어나도 정책대로 동작하는지 확인한다.
이 문서는 성능 테스트 전에 반드시 확인할 시나리오와 대량 seed 실행 기준을 정리한다.

## 검증 범위

현재 검증 대상은 Spring 백엔드가 책임지는 영역이다.

- 사용자별 기억 격리
- scope와 metadata 정합성
- 저장 점수 기준
- 중복 및 유사 기억 방어
- recall threshold
- 만료, 비활성, 삭제 기억 제외
- update, merge, invalidate lifecycle
- event log 기록
- 대량 데이터에서 recall 동작 확인

AI가 담당하는 기억 후보 추출 품질, prompt 주입 방식, 자연어 충돌 판단 품질은 별도 검증 대상이다.

## 단위 테스트 시나리오

### 정책 검증

| 시나리오 | 통과 기준 |
| --- | --- |
| WORKSPACE 기억 저장 | `workspaceKey` 없으면 실패 |
| RESOURCE 기억 저장 | `resourceId` 없으면 실패 |
| SESSION 기억 저장 | `sessionKey` 없으면 실패. 단, `sourceSessionKey`는 metadata에 자동 보정 |
| importance/confidence 기준 | importance 0.5 미만 또는 confidence 0.7 미만 저장 실패 |
| PROJECT_CONTEXT 저장 | 현재 정책상 저장 실패 |

### Recall 검증

| 시나리오 | 통과 기준 |
| --- | --- |
| query recall 유사도 낮음 | 관련 없는 기억이 fallback으로 반환되지 않음 |
| workspace 필터 | 요청한 `workspaceKey`와 일치하는 기억만 반환 |
| session 기본 제외 | `scopeType` 미지정 시 SESSION 기억 제외 |
| 만료 기억 제외 | `expiresAt` 지난 기억 제외 |
| 비활성 기억 제외 | `INACTIVE`, `DELETED` 기억 제외 |

### Lifecycle 검증

| 시나리오 | 통과 기준 |
| --- | --- |
| ADD 중복 content | 기존 기억 반환, 새 row 저장 없음 |
| semantic duplicate | 유사도 높은 기존 기억 반환 |
| UPDATE | 새 기억 저장, 기존 기억 INACTIVE, `supersededByMemoryId` 기록 |
| MERGE | 새 기억 저장, 기존 기억 INACTIVE, MERGED 이벤트 기록 |
| INVALIDATE | 기존 기억 INACTIVE, recall 제외 |

### Event Log 검증

| 동작 | 기대 이벤트 |
| --- | --- |
| 새 기억 저장 | `CREATED` |
| recall 결과 포함 | `RECALLED` |
| update 저장 | `UPDATED` |
| merge 저장 | `MERGED` |
| 기존 기억 비활성화 | `INVALIDATED` |
| 삭제 | `DELETED` |
| 실제 응답 사용 피드백 | `USED` |

## 대량 검증 seed runner

검증용 runner:

```text
src/test/java/com/ssafy/heygent/domain/memory/quality/MemoryQualitySeedRunner.java
```

역할:

- 사용자 100명 기본 생성
- 사용자별 기억 100개 기본 생성
- 특정 heavy user에 기억 1,000개 기본 생성
- `metadata.source = quality-seed`로 seed 데이터 식별
- cleanup 모드 지원

기본 seed 규모:

| 항목 | 기본값 |
| --- | --- |
| 사용자 수 | 100 |
| 사용자별 기억 수 | 100 |
| heavy user 기억 수 | 1,000 |
| 총 기억 수 | 11,000 |

## seed 실행 환경변수

민감값은 파일에 저장하지 않고 실행 환경변수로만 주입한다.

| 환경변수 | 기본값 | 설명 |
| --- | --- | --- |
| `SPRING_DATASOURCE_URL` | `jdbc:postgresql://127.0.0.1:5432/heygent` | DB URL |
| `SPRING_DATASOURCE_USERNAME` | 없음 | DB 사용자 |
| `SPRING_DATASOURCE_PASSWORD` | 없음 | DB 비밀번호 |
| `MEMORY_QUALITY_USERS` | `100` | seed 사용자 수 |
| `MEMORY_QUALITY_MEMORIES_PER_USER` | `100` | 사용자별 기억 수 |
| `MEMORY_QUALITY_HEAVY_USER_MEMORIES` | `1000` | heavy user 기억 수 |
| `MEMORY_QUALITY_CLEANUP` | `false` | true면 seed 데이터 삭제 |

## PowerShell 실행 예시

```powershell
$env:SPRING_DATASOURCE_USERNAME='postgres'
$env:SPRING_DATASOURCE_PASSWORD='<local-password>'
$env:MEMORY_QUALITY_USERS='100'
$env:MEMORY_QUALITY_MEMORIES_PER_USER='100'
$env:MEMORY_QUALITY_HEAVY_USER_MEMORIES='1000'
.\gradlew.bat testClasses
java -cp "build/classes/java/test;build/classes/java/main;build/resources/main" com.ssafy.heygent.domain.memory.quality.MemoryQualitySeedRunner
```

cleanup:

```powershell
$env:MEMORY_QUALITY_CLEANUP='true'
java -cp "build/classes/java/test;build/classes/java/main;build/resources/main" com.ssafy.heygent.domain.memory.quality.MemoryQualitySeedRunner
```

## 성능 확인 기준

초기 로컬 기준 목표:

| 항목 | 목표 |
| --- | --- |
| 전체 seed 11,000건 삽입 | 정상 완료 |
| heavy user recall limit 5 | 정상 응답 |
| 사용자 간 기억 격리 | 다른 userId 기억 미반환 |
| workspace/resource/session 필터 | 조건과 일치하는 기억만 반환 |
| expired/inactive/deleted 제외 | recall 결과 미포함 |

응답 시간 기준은 로컬 PC와 Docker 상태에 따라 달라질 수 있으므로, 첫 측정에서는 수치를 확정하지 않고 baseline을 기록한다.

## 남은 리스크

- OpenAI embedding API 없이 fallback embedding을 쓰면 semantic 품질 검증은 제한적이다.
- seed runner는 service layer가 아니라 DB에 직접 삽입하므로 저장 정책 검증이 아니라 대량 recall/조회 검증용이다.
- pgvector index와 실제 embedding column 품질은 별도 확인이 필요하다.
- AI의 memory candidate 추출 및 prompt condensation 품질은 이 문서 범위 밖이다.
