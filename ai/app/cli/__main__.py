"""``python -m app.cli`` 호환 진입점이다."""

from app.cli.main import main


if __name__ == "__main__":
    raise SystemExit(main())
