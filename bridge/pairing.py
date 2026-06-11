"""브릿지 페어링 API 클라이언트.

브릿지 PC 에서 backend `/api/v1/bridge/pair` 를 호출해 페어링 코드와 디바이스 이름을 토큰으로 교환한다.
표준 라이브러리 urllib 만 사용해 PyInstaller 빌드 의존성을 늘리지 않는다.
"""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass


PAIR_PATH = "/api/v1/bridge/pair"
UNPAIR_PATH = "/api/v1/bridge/unpair"
DEFAULT_TIMEOUT_SECONDS = 10.0


class BridgePairingError(RuntimeError):
    """페어링 API 호출 또는 응답 해석에 실패했음을 나타낸다."""


@dataclass(slots=True)
class BridgePairResult:
    bridge_token: str
    device_id: str
    user_id: str
    device_name: str


def request_pair(
    *,
    api_base_url: str,
    code: str,
    device_name: str,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> BridgePairResult:
    """페어링 코드로 brige_token 을 교환한다.

    네트워크 오류, 코드 만료/오타, 응답 형식 오류는 모두 BridgePairingError 로 변환해서 던진다.
    호출자(GUI) 는 메시지를 그대로 사용자에게 표시한다.
    """

    url = api_base_url.rstrip("/") + PAIR_PATH
    payload = json.dumps({"code": code, "deviceName": device_name}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )

    context = ssl.create_default_context() if url.lower().startswith("https://") else None

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds, context=context) as response:
            body = response.read().decode("utf-8", errors="replace")
            status = response.status
    except urllib.error.HTTPError as exc:
        # 4xx/5xx 본문에 backend 가 ErrorResponse JSON 을 담아 보낸다. 가능한 한 message 만 사용자에게 보인다.
        body = exc.read().decode("utf-8", errors="replace") if exc.fp is not None else ""
        message = _extract_error_message(body) or f"페어링 실패 (HTTP {exc.code})"
        raise BridgePairingError(message) from exc
    except urllib.error.URLError as exc:
        raise BridgePairingError(f"backend 에 연결할 수 없습니다: {exc.reason}") from exc

    if status >= 400:
        raise BridgePairingError(f"페어링 실패 (HTTP {status})")

    try:
        envelope = json.loads(body)
    except json.JSONDecodeError as exc:
        raise BridgePairingError("페어링 응답이 JSON 형식이 아닙니다.") from exc

    data = envelope.get("data") if isinstance(envelope, dict) else None
    if not isinstance(data, dict):
        raise BridgePairingError("페어링 응답에 data 필드가 없습니다.")

    bridge_token = _required_str(data.get("bridgeToken"), "bridgeToken")
    device_id = _required_str(data.get("deviceId"), "deviceId")
    user_id = _required_str(data.get("userId"), "userId")
    device_name_value = data.get("deviceName")
    resolved_device_name = device_name_value if isinstance(device_name_value, str) and device_name_value.strip() else device_name

    return BridgePairResult(
        bridge_token=bridge_token,
        device_id=device_id,
        user_id=user_id,
        device_name=resolved_device_name,
    )


def request_unpair(
    *,
    api_base_url: str,
    bridge_token: str,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> None:
    """브릿지 토큰으로 backend 에 디바이스 해제 요청을 보낸다.

    네트워크 오류, 잘못된 토큰 등은 BridgePairingError 로 변환해 호출자(GUI/트레이) 가 처리한다.
    호출자는 이 함수가 실패하더라도 로컬 토큰 파일은 그래도 지우는 게 좋다 (서버 다운 상태에서도 정리 가능).
    """

    url = api_base_url.rstrip("/") + UNPAIR_PATH
    payload = json.dumps({"bridgeToken": bridge_token}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    context = ssl.create_default_context() if url.lower().startswith("https://") else None

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds, context=context) as response:
            if response.status >= 400:
                raise BridgePairingError(f"해제 실패 (HTTP {response.status})")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace") if exc.fp is not None else ""
        message = _extract_error_message(body) or f"해제 실패 (HTTP {exc.code})"
        raise BridgePairingError(message) from exc
    except urllib.error.URLError as exc:
        raise BridgePairingError(f"backend 에 연결할 수 없습니다: {exc.reason}") from exc


def _required_str(value, field_name: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, int):
        return str(value)
    raise BridgePairingError(f"페어링 응답에 {field_name} 가 없습니다.")


def _extract_error_message(body: str) -> str | None:
    if not body:
        return None
    try:
        envelope = json.loads(body)
    except json.JSONDecodeError:
        return None
    if not isinstance(envelope, dict):
        return None
    for key in ("message", "error", "detail"):
        value = envelope.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None
