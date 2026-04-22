from __future__ import annotations


class SkillLoader:
    """현 단계에서는 동적 skill 파일을 읽지 않고 빈 목록을 돌려준다.

    구조를 미리 나눠 두는 이유는 이후 skill prompt 주입이 생길 때
    tool 구현 파일에 로더 로직을 섞지 않기 위해서다.
    """

    def load_builtin(self) -> list[dict]:
        return []
