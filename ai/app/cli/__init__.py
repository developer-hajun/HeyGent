"""HeyGent CLI 패키지의 공개 호환 표면이다.

기존 코드와 문서가 ``from app.cli import main`` 또는
``from app.cli import RemoteCLIClient`` 형태를 사용하므로,
패키지 내부로 구조를 옮기더라도 자주 쓰는 진입점은 여기서 다시 노출한다.
"""

from app.cli.main import (
    RemoteCLIClient,
    _SlashCommandCompleter,
    _should_open_slash_menu,
    build_parser,
    main,
)

__all__ = [
    "RemoteCLIClient",
    "_SlashCommandCompleter",
    "_should_open_slash_menu",
    "build_parser",
    "main",
]
