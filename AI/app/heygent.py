"""``heygent`` console script 호환 wrapper다.

실제 launcher 구현은 ``app.cli.launcher`` 아래에 둔다. 이렇게 두면
``pyproject.toml``의 ``heygent = app.heygent:main`` 표면은 유지하면서,
CLI 관련 코드는 ``app/cli`` 한 폴더 안에서 관리할 수 있다.
"""

from app.cli.launcher.main import main


__all__ = ["main"]


if __name__ == "__main__":
    raise SystemExit(main())
