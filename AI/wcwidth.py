from __future__ import annotations


def wcswidth(value: str) -> int:
    """테스트 환경용 단순 폭 계산기.

    실제 wcwidth 가 없을 때는 정밀한 동아시아 폭 계산 대신
    문자열 길이를 그대로 돌려 최소 렌더링 테스트를 가능하게 한다.
    """

    return len(value)
