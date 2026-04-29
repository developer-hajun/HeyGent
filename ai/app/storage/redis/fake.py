from __future__ import annotations

from collections import defaultdict
from typing import Any


class FakeRedis:
    """Redis 서버 없이 projection 계약을 검증하기 위한 최소 인메모리 구현이다."""

    def __init__(self, *, decode_responses: bool = True) -> None:
        self.decode_responses = decode_responses
        self._strings: dict[str, str] = {}
        self._ttls: dict[str, int] = {}
        self._zsets: dict[str, dict[str, float]] = defaultdict(dict)

    def set(self, name: str, value: str, ex: int | None = None) -> bool:
        self._strings[name] = value
        if ex is not None:
            self._ttls[name] = ex
        elif name in self._ttls:
            del self._ttls[name]
        return True

    def get(self, name: str) -> str | None:
        value = self._strings.get(name)
        if value is None or self.decode_responses:
            return value
        return value.encode("utf-8")

    def ttl(self, name: str) -> int:
        return self._ttls.get(name, -1 if name in self._strings else -2)

    def incr(self, name: str) -> int:
        next_value = int(self._strings.get(name, "0")) + 1
        self._strings[name] = str(next_value)
        return next_value

    def zadd(self, name: str, mapping: dict[str, int | float]) -> int:
        added = 0
        zset = self._zsets[name]
        for member, score in mapping.items():
            if member not in zset:
                added += 1
            zset[member] = float(score)
        return added

    def expire(self, name: str, seconds: int) -> bool:
        if name not in self._strings and name not in self._zsets:
            return False
        self._ttls[name] = seconds
        return True

    def zrange(self, name: str, start: int, end: int, *, withscores: bool = False) -> list[Any]:
        items = sorted(self._zsets.get(name, {}).items(), key=lambda item: (item[1], item[0]))
        sliced = self._slice(items, start, end)
        if withscores:
            return sliced
        return [self._encode(member) for member, _score in sliced]

    def zrem(self, name: str, *members: str) -> int:
        zset = self._zsets.get(name, {})
        removed = 0
        for member in members:
            normalized = member.decode("utf-8") if isinstance(member, bytes) else member
            if normalized in zset:
                del zset[normalized]
                removed += 1
        return removed

    def zremrangebyscore(self, name: str, min_score: int | float | str, max_score: int | float | str) -> int:
        zset = self._zsets.get(name, {})
        lower = float(min_score)
        upper = float(max_score)
        removable = [member for member, score in zset.items() if lower <= score <= upper]
        for member in removable:
            del zset[member]
        return len(removable)

    def zremrangebyrank(self, name: str, start: int, end: int) -> int:
        items = sorted(self._zsets.get(name, {}).items(), key=lambda item: (item[1], item[0]))
        removable = self._slice(items, start, end)
        for member, _score in removable:
            del self._zsets[name][member]
        return len(removable)

    def _encode(self, value: str) -> str | bytes:
        if self.decode_responses:
            return value
        return value.encode("utf-8")

    @staticmethod
    def _slice(items: list[Any], start: int, end: int) -> list[Any]:
        if end == -1:
            return items[start:]
        return items[start : end + 1]
