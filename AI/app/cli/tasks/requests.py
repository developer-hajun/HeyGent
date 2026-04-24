from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from app.cli.core.transport import request_path
from app.core.config import Settings


def load_payload(raw: str | None) -> dict[str, Any]:
    """문자열 JSON 또는 파일 경로에서 task payload 를 읽는다."""

    if not raw:
        return {}

    candidate = Path(raw)
    if candidate.exists():
        return json.loads(candidate.read_text(encoding="utf-8"))
    return json.loads(raw)


def build_task_input_payload(args) -> dict[str, Any]:
    """CLI 인자를 TaskRun input_payload 로 정규화한다."""

    payload = load_payload(args.payload)
    if args.prompt is not None:
        payload = {**payload, "prompt": args.prompt}
    return payload


def run_model_check_task(client, settings: Settings, prompt: str) -> httpx.Response | Any:
    """연결 직후 실제 모델 작업을 바로 검증한다."""

    return client.request(
        "POST",
        request_path(settings, "/taskRuns"),
        json_body={
            "intent_type": "model.generate",
            "owner_key": "cli-user",
            "input_payload": {"prompt": prompt},
        },
    )


def run_prompt_task(client, settings: Settings, prompt: str):
    """대화형 셸 일반 입력을 `model.generate` TaskRun 으로 보낸다."""

    return client.request(
        "POST",
        request_path(settings, "/taskRuns"),
        json_body={
            "intent_type": "model.generate",
            "owner_key": "cli-user",
            "input_payload": {"prompt": prompt},
        },
    )
