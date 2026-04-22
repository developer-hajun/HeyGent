# Storage Migrations

현재 런타임은 `SQLiteTaskRepository` 초기화 시점에 canonical schema 를 보정한다.
보정 자체는 `app/storage/migrations/runtime.py` 의 migration registry 로 관리하며,
적용 내역은 SQLite `schema_migrations` 테이블에 남긴다.

이 폴더는 이후 수동/배포형 migration SQL 또는 Python migration 을 누적하는 기준점으로 둔다.
`flow_name` 같은 legacy 축을 다시 추가하지 않고, `TaskRun.current_step_run_id`,
`TaskRun.intent_type`, `TaskRun.entry_capability`, `StepRun.executor_key` 같은
loop-first anchor 만 canonical schema 로 유지한다.
