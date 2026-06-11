from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class SessionSource:
    """외부 연결에서 들어온 세션 출처를 단순화한 모델이다."""

    platform: str
    channel_id: str
    channel_name: str | None = None
    channel_type: str = "dm"
    user_id: str | None = None
    user_name: str | None = None
    thread_id: str | None = None
    channel_topic: str | None = None
    user_id_alt: str | None = None
    channel_id_alt: str | None = None
    is_bot: bool = False

    @property
    def description(self) -> str:
        if self.platform == "local":
            return "local shell"

        parts: list[str] = []
        if self.channel_type == "dm":
            parts.append(f"DM with {self.user_name or self.user_id or 'user'}")
        elif self.channel_type == "group":
            parts.append(f"group: {self.channel_name or self.channel_id}")
        elif self.channel_type == "channel":
            parts.append(f"channel: {self.channel_name or self.channel_id}")
        else:
            parts.append(self.channel_name or self.channel_id)

        if self.thread_id:
            parts.append(f"thread: {self.thread_id}")
        return ", ".join(parts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "channel_id": self.channel_id,
            "channel_name": self.channel_name,
            "channel_type": self.channel_type,
            "user_id": self.user_id,
            "user_name": self.user_name,
            "thread_id": self.thread_id,
            "channel_topic": self.channel_topic,
            "user_id_alt": self.user_id_alt,
            "channel_id_alt": self.channel_id_alt,
            "is_bot": self.is_bot,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "SessionSource":
        return cls(
            platform=str(payload["platform"]),
            channel_id=str(payload["channel_id"]),
            channel_name=payload.get("channel_name"),
            channel_type=str(payload.get("channel_type") or "dm"),
            user_id=payload.get("user_id"),
            user_name=payload.get("user_name"),
            thread_id=payload.get("thread_id"),
            channel_topic=payload.get("channel_topic"),
            user_id_alt=payload.get("user_id_alt"),
            channel_id_alt=payload.get("channel_id_alt"),
            is_bot=bool(payload.get("is_bot", False)),
        )


@dataclass(slots=True)
class SessionContext:
    """프롬프트에 넣을 대화 세션 문맥이다."""

    source: SessionSource
    connected_platforms: list[str] = field(default_factory=list)
    home_channels: dict[str, dict[str, Any]] = field(default_factory=dict)
    shared_multi_user_session: bool = False
    session_key: str = ""
    session_id: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source.to_dict(),
            "connected_platforms": list(self.connected_platforms),
            "home_channels": dict(self.home_channels),
            "shared_multi_user_session": self.shared_multi_user_session,
            "session_key": self.session_key,
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


def build_session_context_prompt(context: SessionContext) -> str:
    """세션 정보를 모델이 읽을 수 있는 프롬프트 문맥으로 바꾼다."""

    lines = [
        "## Current Session Context",
        "",
        f"Source: {context.source.platform} ({context.source.description})",
        f"Session key: {context.session_key or '-'}",
        f"Session id: {context.session_id or '-'}",
    ]

    if context.source.channel_topic:
        lines.append(f"Channel topic: {context.source.channel_topic}")

    if context.shared_multi_user_session:
        lines.append("Session type: multi-user session")
    elif context.source.user_name:
        lines.append(f"User: {context.source.user_name}")
    elif context.source.user_id:
        lines.append(f"User ID: {context.source.user_id}")

    platforms = ["local (files on this machine)"]
    for platform in context.connected_platforms:
        if platform != "local":
            platforms.append(f"{platform}: connected")
    lines.append(f"Connected platforms: {', '.join(platforms)}")

    if context.home_channels:
        lines.append("")
        lines.append("Home channels:")
        for platform, home in context.home_channels.items():
            lines.append(f"- {platform}: {home.get('name') or home.get('channel_id') or '-'}")

    lines.append("")
    lines.append("Delivery options:")
    if context.source.platform == "local":
        lines.append('- "origin" -> local shell')
    else:
        lines.append(f'- "origin" -> {context.source.channel_name or context.source.channel_id}')
    lines.append('- "local" -> local files / local shell')

    for platform in sorted(context.home_channels):
        lines.append(f'- "{platform}" -> configured home channel')

    return "\n".join(lines)


def build_session_key(
    source: SessionSource,
    *,
    group_sessions_per_user: bool = True,
    thread_sessions_per_user: bool = False,
) -> str:
    """같은 대화를 다시 찾기 위한 안정적인 session key를 만든다."""

    platform = source.platform
    if source.channel_type == "dm":
        if source.channel_id:
            if source.thread_id:
                return f"agent:main:{platform}:dm:{source.channel_id}:{source.thread_id}"
            return f"agent:main:{platform}:dm:{source.channel_id}"
        if source.thread_id:
            return f"agent:main:{platform}:dm:{source.thread_id}"
        return f"agent:main:{platform}:dm"

    participant_id = source.user_id_alt or source.user_id
    key_parts = ["agent:main", platform, source.channel_type]

    if source.channel_id:
        key_parts.append(source.channel_id)
    if source.thread_id:
        key_parts.append(source.thread_id)

    isolate_user = group_sessions_per_user
    if source.thread_id and not thread_sessions_per_user:
        isolate_user = False

    if isolate_user and participant_id:
        key_parts.append(str(participant_id))

    return ":".join(key_parts)
