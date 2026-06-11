from __future__ import annotations

from dataclasses import dataclass
import difflib
import fnmatch
import os
import re
from pathlib import Path
from typing import Any

from app.tools.runtime.catalog import register_runtime_tool_definition


MAX_READ_BYTES = 1_000_000
MAX_WRITE_CHARS = 1_000_000
MAX_SEARCH_FILE_BYTES = 1_000_000
MAX_READ_LINES = 2_000
MAX_SEARCH_LIMIT = 500
SKIPPED_DIRS = {".git", ".hg", ".svn", "__pycache__", ".pytest_cache", ".venv", "node_modules"}
SECRET_KEY_PATTERN = re.compile(
    r"(?i)\b("
    r"[A-Z0-9_.-]*(?:"
    r"database[_-]?url|db[_-]?url|redis[_-]?url|mongo[_-]?url|connection[_-]?string|dsn|"
    r"auth|credential|client[_-]?secret|webhook[_-]?secret|cookie|session|jwt|bearer|"
    r"api[_-]?key|key|token|password|passwd|secret|access[_-]?key|private[_-]?key"
    r")[A-Z0-9_.-]*"
    r"\s*[:=]\s*)"
    r"(?:(['\"])([^\r\n]*?)\2|([^\s#]+))"
)
LONG_TOKEN_PATTERN = re.compile(r"(?<![A-Za-z0-9_./+=-])(?=[A-Za-z0-9_./+=-]{32,})(?=.*[A-Za-z])(?=.*\d)[A-Za-z0-9_./+=-]+")
PRIVATE_KEY_MARKER_PATTERN = re.compile(r"-----BEGIN [^-]*PRIVATE KEY-----|-----END [^-]*PRIVATE KEY-----")


READ_FILE_SCHEMA = {
    "name": "read_file",
    "description": "Read a text file inside the workspace with line-numbered pagination.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Workspace-relative file path to read."},
            "offset": {"type": "integer", "description": "1-based first line to return.", "default": 1},
            "limit": {"type": "integer", "description": "Maximum number of lines to return.", "default": 500},
        },
        "required": ["path"],
    },
}

WRITE_FILE_SCHEMA = {
    "name": "write_file",
    "description": (
        "Write a text file inside the workspace, creating parent directories when needed. "
        "If the user provided a directory as the save location, choose a meaningful file name inside that directory; "
        "do not turn the directory path itself into a file by appending an extension."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Workspace-relative file path to write. Must include the final file name, not only a directory.",
            },
            "content": {"type": "string", "description": "Complete text content to write."},
        },
        "required": ["path", "content"],
    },
}

PATCH_SCHEMA = {
    "name": "patch",
    "description": "Patch files inside the workspace with replace mode or patch format.",
    "parameters": {
        "type": "object",
        "properties": {
            "mode": {
                "type": "string",
                "enum": ["replace", "patch"],
                "description": "replace edits one file by string replacement; patch applies a patch block.",
                "default": "replace",
            },
            "path": {"type": "string", "description": "File path for replace mode."},
            "old_string": {"type": "string", "description": "Text to replace in replace mode."},
            "new_string": {"type": "string", "description": "Replacement text in replace mode."},
            "replace_all": {"type": "boolean", "description": "Replace every occurrence.", "default": False},
            "patch": {"type": "string", "description": "Patch text starting with *** Begin Patch."},
        },
        "required": ["mode"],
    },
}


@dataclass(frozen=True)
class _PatchOperation:
    kind: str
    path: Path
    rel_path: str
    original: str | None = None
    updated: str | None = None
    source: Path | None = None
    source_rel_path: str | None = None


@dataclass(frozen=True)
class _UpdateBlock:
    lines: list[str]
    hint: str = ""

SEARCH_FILES_SCHEMA = {
    "name": "search_files",
    "description": "Search text file contents or find files by name inside the workspace.",
    "parameters": {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Regex for content search or glob for file search."},
            "query": {"type": "string", "description": "Alias for pattern."},
            "target": {
                "type": "string",
                "enum": ["content", "files"],
                "description": "content searches file contents; files searches file paths.",
                "default": "content",
            },
            "path": {"type": "string", "description": "Workspace-relative file or directory to search.", "default": "."},
            "file_glob": {"type": "string", "description": "Optional glob filter for content search."},
            "limit": {"type": "integer", "description": "Maximum number of results.", "default": 50},
            "offset": {"type": "integer", "description": "Number of results to skip.", "default": 0},
            "output_mode": {
                "type": "string",
                "enum": ["content", "files_only", "count"],
                "description": "Output shape for content search.",
                "default": "content",
            },
            "context": {"type": "integer", "description": "Context lines around matches.", "default": 0},
        },
        "required": [],
    },
}


_READ_FILE_TOOL_DEFINITION = register_runtime_tool_definition(
    name="read_file",
    toolset="file",
    module="app.tools.file.file_tools",
    summary="Read a text file inside the workspace with pagination.",
    schema=READ_FILE_SCHEMA,
)
_WRITE_FILE_TOOL_DEFINITION = register_runtime_tool_definition(
    name="write_file",
    toolset="file",
    module="app.tools.file.file_tools",
    summary="Write a text file inside the workspace.",
    schema=WRITE_FILE_SCHEMA,
)
_PATCH_TOOL_DEFINITION = register_runtime_tool_definition(
    name="patch",
    toolset="file",
    module="app.tools.file.file_tools",
    summary="Patch files inside the workspace.",
    schema=PATCH_SCHEMA,
)
_SEARCH_FILES_TOOL_DEFINITION = register_runtime_tool_definition(
    name="search_files",
    toolset="file",
    module="app.tools.file.file_tools",
    summary="Search files inside the workspace.",
    schema=SEARCH_FILES_SCHEMA,
)


def file_tool_definitions() -> list[dict[str, object]]:
    return [
        _definition_payload(_READ_FILE_TOOL_DEFINITION),
        _definition_payload(_WRITE_FILE_TOOL_DEFINITION),
        _definition_payload(_PATCH_TOOL_DEFINITION),
        _definition_payload(_SEARCH_FILES_TOOL_DEFINITION),
    ]


def read_file(args: dict[str, Any]) -> dict[str, Any]:
    target = _resolve_read_workspace_path(args.get("path"), workspace_root=args.get("workspace_root"))
    if target.is_dir():
        raise IsADirectoryError(_display_path(target, _workspace_root(args.get("workspace_root"))))
    content = _read_text_file(target, max_bytes=MAX_READ_BYTES)
    lines = _redact_secret_content(content).splitlines()
    offset = _coerce_int(args.get("offset"), default=1, minimum=1)
    limit = _coerce_int(args.get("limit"), default=500, minimum=1, maximum=MAX_READ_LINES)
    start_index = offset - 1
    selected = lines[start_index : start_index + limit]
    numbered = "\n".join(f"{line_number}|{line}" for line_number, line in enumerate(selected, start=offset))
    return {
        "path": _display_path(target, _workspace_root(args.get("workspace_root"))),
        "content": numbered,
        "offset": offset,
        "limit": limit,
        "total_lines": len(lines),
        "returned_lines": len(selected),
        "truncated": start_index + len(selected) < len(lines),
    }


def write_file(args: dict[str, Any]) -> dict[str, Any]:
    content = args.get("content")
    if not isinstance(content, str):
        raise TypeError("content must be a string")
    if len(content) > MAX_WRITE_CHARS:
        raise ValueError("content is too large")

    root = _workspace_root(args.get("workspace_root"))
    target = _resolve_workspace_path(args.get("path"), workspace_root=root)
    if target.exists() and target.is_dir():
        raise IsADirectoryError(_display_path(target, root))

    parent_existed = target.parent.exists()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8", newline="")
    return {
        "path": _display_path(target, root),
        "bytes_written": len(content.encode("utf-8")),
        "lines_written": len(content.splitlines()),
        "dirs_created": not parent_existed,
    }


def patch(args: dict[str, Any]) -> dict[str, Any]:
    mode = str(args.get("mode") or "replace")
    if mode == "apply_patch":
        mode = "patch"
    if mode == "replace":
        return _patch_replace(args)
    if mode == "patch":
        patch_text = args.get("patch")
        if not isinstance(patch_text, str) or not patch_text.strip():
            raise ValueError("patch is required for patch mode")
        return _apply_patch_text(patch_text, workspace_root=args.get("workspace_root"))
    raise ValueError(f"unsupported patch mode: {mode}")


def search_files(args: dict[str, Any]) -> dict[str, Any]:
    # 일부 호출자는 검색어 이름으로 query를 사용하므로 pattern과 같은 의미로 처리한다.
    pattern = args.get("pattern") if args.get("pattern") is not None else args.get("query")
    if not isinstance(pattern, str) or not pattern:
        raise ValueError("pattern is required")

    root = _workspace_root(args.get("workspace_root"))
    search_root = _resolve_read_workspace_path(args.get("path") or ".", workspace_root=root)
    if not search_root.exists():
        raise FileNotFoundError(_display_path(search_root, root))

    target = str(args.get("target") or "content")
    offset = _coerce_int(args.get("offset"), default=0, minimum=0)
    limit = _coerce_int(args.get("limit"), default=50, minimum=1, maximum=MAX_SEARCH_LIMIT)
    if target == "files":
        return _search_file_names(root=root, search_root=search_root, pattern=pattern, offset=offset, limit=limit)
    if target == "content":
        return _search_file_content(root=root, search_root=search_root, args=args, pattern=pattern, offset=offset, limit=limit)
    raise ValueError("target must be content or files")


def _handle_read_file(args: dict[str, Any], **_: Any) -> dict[str, Any]:
    return read_file(args)


def _handle_write_file(args: dict[str, Any], **_: Any) -> dict[str, Any]:
    return write_file(args)


def _handle_patch(args: dict[str, Any], **_: Any) -> dict[str, Any]:
    return patch(args)


def _handle_search_files(args: dict[str, Any], **_: Any) -> dict[str, Any]:
    return search_files(args)


read_file_handler = read_file
write_file_handler = write_file
patch_handler = patch
search_files_handler = search_files


def _definition_payload(definition: Any) -> dict[str, object]:
    return {
        "name": definition.name,
        "toolset": definition.toolset,
        "module": definition.module,
        "summary": definition.summary,
        "schema": definition.schema,
        "result_format": definition.result_format,
    }


def _workspace_root(value: Any = None) -> Path:
    raw_root = value or os.environ.get("HEYGENT_WORKSPACE_ROOT") or os.environ.get("TERMINAL_CWD") or os.getcwd()
    return Path(str(raw_root)).expanduser().resolve()


def _resolve_workspace_path(value: Any, *, workspace_root: Any = None) -> Path:
    return _resolve_read_workspace_path(value, workspace_root=workspace_root)


def _resolve_read_workspace_path(value: Any, *, workspace_root: Any = None) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("path is required")
    root = _workspace_root(workspace_root)
    raw_path = _coerce_workspace_path(value, root=root)
    candidate = raw_path if raw_path.is_absolute() else root / raw_path
    resolved = candidate.resolve(strict=False)
    # workspace guard: 모델이 절대 경로나 ..를 넘겨도 루트 밖 파일에는 접근하지 않는다.
    if not _is_relative_to(resolved, root):
        raise PermissionError("path must stay inside the workspace")
    return resolved


def _coerce_workspace_path(value: str, *, root: Path) -> Path:
    text = value.strip()
    normalized = text.replace("\\", "/")
    # 브라우저 사용자가 Windows 절대 경로를 붙여 넣어도 컨테이너 안에서는 bind mount된
    # workspace 기준 상대 경로로 바꿔야 실제 호스트 파일에 닿는다.
    if re.match(r"^[A-Za-z]:/", normalized):
        for workspace_name in _workspace_path_markers(root):
            workspace_marker = f"/{workspace_name}/"
            if workspace_marker in normalized:
                normalized = normalized.split(workspace_marker, 1)[1]
                break
        else:
            if os.name != "nt":
                return Path("/") / normalized
    return Path(normalized).expanduser()


def _workspace_path_markers(root: Path) -> list[str]:
    markers = [root.name]
    host_workspace_name = str(os.environ.get("HEYGENT_HOST_WORKSPACE_BASENAME") or "").strip()
    if host_workspace_name:
        markers.append(host_workspace_name)
    return list(dict.fromkeys(markers))


def _relative_path(path: Path, root: Path) -> Path:
    try:
        return path.relative_to(root)
    except ValueError:
        return path


def _display_path(path: Path, root: Path) -> str:
    return _relative_path(path, root).as_posix()


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _coerce_int(value: Any, *, default: int, minimum: int, maximum: int | None = None) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError):
        result = default
    result = max(minimum, result)
    if maximum is not None:
        result = min(maximum, result)
    return result


def _read_text_file(path: Path, *, max_bytes: int) -> str:
    if not path.exists():
        raise FileNotFoundError(str(path))
    if not path.is_file():
        raise IsADirectoryError(str(path))
    size = path.stat().st_size
    if size > max_bytes:
        raise ValueError("file is too large")
    data = path.read_bytes()
    if b"\x00" in data:
        raise ValueError("binary files are not supported")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("file is not valid utf-8 text") from error


def _patch_replace(args: dict[str, Any]) -> dict[str, Any]:
    root = _workspace_root(args.get("workspace_root"))
    target = _resolve_workspace_path(args.get("path"), workspace_root=root)
    old_string = args.get("old_string")
    new_string = args.get("new_string")
    if not isinstance(old_string, str) or old_string == "":
        raise ValueError("old_string is required")
    if not isinstance(new_string, str):
        raise TypeError("new_string must be a string")

    original = _read_text_file(target, max_bytes=MAX_READ_BYTES)
    count = original.count(old_string)
    if count == 0:
        raise ValueError("old_string was not found")
    replace_all = bool(args.get("replace_all", False))
    if count > 1 and not replace_all:
        raise ValueError("old_string must be unique unless replace_all is true")

    updated = original.replace(old_string, new_string) if replace_all else original.replace(old_string, new_string, 1)
    target.write_text(updated, encoding="utf-8", newline="")
    rel_path = _display_path(target, root)
    return {
        "success": True,
        "mode": "replace",
        "path": rel_path,
        "replacements": count if replace_all else 1,
        "diff": _redact_secret_content(_build_diff(original, updated, rel_path)),
        "files_modified": [rel_path],
    }


def _apply_patch_text(patch_text: str, *, workspace_root: Any = None) -> dict[str, Any]:
    root = _workspace_root(workspace_root)
    lines = patch_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    if not lines or lines[0] != "*** Begin Patch" or lines[-1] != "*** End Patch":
        raise ValueError("patch must start with *** Begin Patch and end with *** End Patch")

    index = 1
    state: dict[Path, str | None] = {}
    operations: list[_PatchOperation] = []
    while index < len(lines) - 1:
        line = lines[index]
        if line.startswith("*** Add File: "):
            index, operation = _plan_add_file(lines, index, root, state)
            operations.append(operation)
            continue
        if line.startswith("*** Delete File: "):
            index, operation = _plan_delete_file(lines, index, root, state)
            operations.append(operation)
            continue
        if line.startswith("*** Update File: "):
            index, operation = _plan_update_file(lines, index, root, state)
            operations.append(operation)
            continue
        if line.startswith("*** Move File: "):
            index, operation = _plan_move_file(lines, index, root, state)
            operations.append(operation)
            continue
        raise ValueError(f"unsupported patch line: {line}")

    _commit_patch_operations(operations)
    diffs = [_operation_diff(operation) for operation in operations]
    modified = [operation.rel_path for operation in operations if operation.kind == "update"]
    created = [operation.rel_path for operation in operations if operation.kind == "add"]
    deleted = [operation.rel_path for operation in operations if operation.kind == "delete"]
    moved = [
        {"from": operation.source_rel_path, "to": operation.rel_path}
        for operation in operations
        if operation.kind == "move"
    ]
    return {
        "success": True,
        "mode": "patch",
        "diff": "\n".join(item for item in diffs if item),
        "files_modified": modified,
        "files_created": created,
        "files_deleted": deleted,
        "files_moved": moved,
    }


def _plan_add_file(
    lines: list[str],
    index: int,
    root: Path,
    state: dict[Path, str | None],
) -> tuple[int, _PatchOperation]:
    target = _resolve_workspace_path(lines[index].removeprefix("*** Add File: "), workspace_root=root)
    if _virtual_exists(target, state):
        raise FileExistsError(_display_path(target, root))
    index += 1
    content_lines: list[str] = []
    while index < len(lines) and not _is_patch_file_header(lines[index]) and lines[index] != "*** End Patch":
        line = lines[index]
        if not line.startswith("+"):
            raise ValueError("add file lines must start with +")
        content_lines.append(line[1:])
        index += 1

    content = "\n".join(content_lines)
    if content_lines:
        content += "\n"
    if len(content) > MAX_WRITE_CHARS:
        raise ValueError("content is too large")
    rel_path = _display_path(target, root)
    state[target] = content
    return index, _PatchOperation(kind="add", path=target, rel_path=rel_path, original="", updated=content)


def _plan_delete_file(
    lines: list[str],
    index: int,
    root: Path,
    state: dict[Path, str | None],
) -> tuple[int, _PatchOperation]:
    target = _resolve_workspace_path(lines[index].removeprefix("*** Delete File: "), workspace_root=root)
    original = _virtual_read_text(target, state)
    rel_path = _display_path(target, root)
    state[target] = None
    return index + 1, _PatchOperation(kind="delete", path=target, rel_path=rel_path, original=original, updated="")


def _plan_update_file(
    lines: list[str],
    index: int,
    root: Path,
    state: dict[Path, str | None],
) -> tuple[int, _PatchOperation]:
    target = _resolve_workspace_path(lines[index].removeprefix("*** Update File: "), workspace_root=root)
    original = _virtual_read_text(target, state)
    body: list[str] = []
    index += 1
    while index < len(lines) and not _is_patch_file_header(lines[index]) and lines[index] != "*** End Patch":
        body.append(lines[index])
        index += 1

    updated = _apply_update_body(original, body)
    if len(updated) > MAX_WRITE_CHARS:
        raise ValueError("content is too large")
    rel_path = _display_path(target, root)
    state[target] = updated
    return index, _PatchOperation(kind="update", path=target, rel_path=rel_path, original=original, updated=updated)


def _plan_move_file(
    lines: list[str],
    index: int,
    root: Path,
    state: dict[Path, str | None],
) -> tuple[int, _PatchOperation]:
    source, destination = _parse_move_paths(lines[index], root)
    if not _virtual_exists(source, state):
        raise FileNotFoundError(_display_path(source, root))
    if _virtual_exists(destination, state):
        raise FileExistsError(_display_path(destination, root))

    content = _virtual_read_text(source, state)
    source_rel_path = _display_path(source, root)
    destination_rel_path = _display_path(destination, root)
    state[source] = None
    state[destination] = content
    return (
        index + 1,
        _PatchOperation(
            kind="move",
            path=destination,
            rel_path=destination_rel_path,
            original=content,
            updated=content,
            source=source,
            source_rel_path=source_rel_path,
        ),
    )


def _apply_update_body(original: str, body: list[str]) -> str:
    had_trailing_newline = original.endswith("\n")
    current_lines = original.splitlines()
    blocks = _split_update_blocks(body)
    for block in blocks:
        old_block = [line[1:] for line in block.lines if line.startswith((" ", "-"))]
        new_block = [line[1:] for line in block.lines if line.startswith((" ", "+"))]
        if old_block:
            start = _find_unique_block(current_lines, old_block, hint=block.hint)
            current_lines[start : start + len(old_block)] = new_block
            continue

        additions = [line[1:] for line in block.lines if line.startswith("+")]
        if not additions:
            raise ValueError("empty update hunks are not supported")
        start = _find_addition_index(current_lines, block.hint)
        current_lines[start:start] = additions

    updated = "\n".join(current_lines)
    if had_trailing_newline or (blocks and _block_adds_trailing_line(blocks[-1].lines)):
        updated += "\n"
    return updated


def _split_update_blocks(body: list[str]) -> list[_UpdateBlock]:
    blocks: list[_UpdateBlock] = []
    current: list[str] = []
    current_hint = ""
    for line in body:
        if line.startswith("@@"):
            if current:
                blocks.append(_UpdateBlock(lines=current, hint=current_hint))
                current = []
            current_hint = _normalize_hunk_hint(line)
            continue
        if not line or line[0] not in {" ", "-", "+"}:
            raise ValueError("update hunk lines must start with space, -, or +")
        current.append(line)
    if current:
        blocks.append(_UpdateBlock(lines=current, hint=current_hint))
    if not blocks:
        raise ValueError("update patch must include at least one hunk")
    return blocks


def _find_unique_block(lines: list[str], block: list[str], *, hint: str = "") -> int:
    if not block:
        raise ValueError("empty update hunks are not supported")
    matches = [
        index
        for index in range(0, len(lines) - len(block) + 1)
        if lines[index : index + len(block)] == block
    ]
    if not matches:
        raise ValueError("patch hunk did not match file content")
    if hint and len(matches) > 1:
        hint_indices = _find_hint_indices(lines, hint)
        hinted_matches = [index for index in matches if any(index >= hint_index for hint_index in hint_indices)]
        if len(hinted_matches) == 1:
            return hinted_matches[0]
    if len(matches) > 1:
        raise ValueError("patch hunk matched multiple locations")
    return matches[0]


def _find_addition_index(lines: list[str], hint: str) -> int:
    if not hint:
        return len(lines)
    hint_indices = _find_hint_indices(lines, hint)
    if len(hint_indices) != 1:
        raise ValueError("patch hunk context hint matched multiple locations")
    return hint_indices[0] + 1


def _find_hint_indices(lines: list[str], hint: str) -> list[int]:
    matches = [index for index, line in enumerate(lines) if hint in line]
    if not matches:
        raise ValueError("patch hunk context hint did not match file content")
    return matches


def _normalize_hunk_hint(line: str) -> str:
    hint = line[2:].strip()
    if hint.endswith("@@"):
        hint = hint[:-2].strip()
    return hint


def _block_adds_trailing_line(block: list[str]) -> bool:
    return bool(block and block[-1].startswith(("+", " ")))


def _is_patch_file_header(line: str) -> bool:
    return (
        line.startswith("*** Add File: ")
        or line.startswith("*** Delete File: ")
        or line.startswith("*** Update File: ")
        or line.startswith("*** Move File: ")
    )


def _parse_move_paths(line: str, root: Path) -> tuple[Path, Path]:
    payload = line.removeprefix("*** Move File: ")
    source_text, separator, destination_text = payload.partition(" -> ")
    if not separator or not source_text.strip() or not destination_text.strip():
        raise ValueError("move file must use *** Move File: src -> dst")
    source = _resolve_workspace_path(source_text.strip(), workspace_root=root)
    destination = _resolve_workspace_path(destination_text.strip(), workspace_root=root)
    if source == destination:
        raise ValueError("move source and destination must differ")
    return source, destination


def _virtual_exists(path: Path, state: dict[Path, str | None]) -> bool:
    if path in state:
        return state[path] is not None
    return path.exists()


def _virtual_read_text(path: Path, state: dict[Path, str | None]) -> str:
    if path in state:
        content = state[path]
        if content is None:
            raise FileNotFoundError(str(path))
        return content
    return _read_text_file(path, max_bytes=MAX_READ_BYTES)


def _commit_patch_operations(operations: list[_PatchOperation]) -> None:
    # 여러 파일 patch는 중간 실패 시 앞서 쓴 파일을 되돌릴 수 있도록 먼저 snapshot을 잡는다.
    snapshots = _snapshot_patch_paths(operations)
    try:
        for operation in operations:
            if operation.kind in {"add", "update"}:
                operation.path.parent.mkdir(parents=True, exist_ok=True)
                operation.path.write_text(operation.updated or "", encoding="utf-8", newline="")
            elif operation.kind == "delete":
                operation.path.unlink()
            elif operation.kind == "move":
                if operation.source is None:
                    raise ValueError("move operation source is missing")
                operation.path.parent.mkdir(parents=True, exist_ok=True)
                operation.source.unlink()
                operation.path.write_text(operation.updated or "", encoding="utf-8", newline="")
    except Exception:
        # rollback은 patch 호출 하나가 부분 적용 상태로 남지 않게 하는 최소 안전장치다.
        _restore_patch_snapshots(snapshots)
        raise


def _snapshot_patch_paths(operations: list[_PatchOperation]) -> dict[Path, bytes | None]:
    paths: list[Path] = []
    for operation in operations:
        if operation.source is not None:
            paths.append(operation.source)
        paths.append(operation.path)

    snapshots: dict[Path, bytes | None] = {}
    for path in paths:
        if path in snapshots:
            continue
        snapshots[path] = path.read_bytes() if path.is_file() else None
    return snapshots


def _restore_patch_snapshots(snapshots: dict[Path, bytes | None]) -> None:
    for path, data in snapshots.items():
        if data is None:
            if path.is_file():
                path.unlink()
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def _operation_diff(operation: _PatchOperation) -> str:
    if operation.kind == "move":
        source_diff = _build_diff(operation.original or "", "", operation.source_rel_path or operation.rel_path)
        destination_diff = _build_diff("", operation.updated or "", operation.rel_path)
        return _redact_secret_content(source_diff + destination_diff)
    return _redact_secret_content(_build_diff(operation.original or "", operation.updated or "", operation.rel_path))


def _search_file_names(*, root: Path, search_root: Path, pattern: str, offset: int, limit: int) -> dict[str, Any]:
    files = [
        _display_path(path, root)
        for path in _iter_files(search_root, root=root)
        if fnmatch.fnmatch(_display_path(path, root), pattern) or fnmatch.fnmatch(path.name, pattern)
    ]
    files.sort()
    selected = files[offset : offset + limit]
    return {
        "target": "files",
        "pattern": pattern,
        "files": selected,
        "total_count": len(files),
        "offset": offset,
        "limit": limit,
        "truncated": offset + len(selected) < len(files),
    }


def _search_file_content(*, root: Path, search_root: Path, args: dict[str, Any], pattern: str, offset: int, limit: int) -> dict[str, Any]:
    try:
        regex = re.compile(pattern)
    except re.error as error:
        raise ValueError(f"invalid regex pattern: {error}") from error

    file_glob = args.get("file_glob")
    output_mode = str(args.get("output_mode") or "content")
    context = _coerce_int(args.get("context"), default=0, minimum=0, maximum=20)
    matches: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    files_with_matches: set[str] = set()

    for path in _iter_files(search_root, root=root):
        rel_path = _display_path(path, root)
        if isinstance(file_glob, str) and file_glob and not (
            fnmatch.fnmatch(path.name, file_glob) or fnmatch.fnmatch(rel_path, file_glob)
        ):
            continue
        try:
            text = _read_text_file(path, max_bytes=MAX_SEARCH_FILE_BYTES)
        except (OSError, ValueError):
            continue
        file_lines = text.splitlines()
        for line_index, line in enumerate(file_lines):
            if not regex.search(line):
                continue
            line_number = line_index + 1
            counts[rel_path] = counts.get(rel_path, 0) + 1
            files_with_matches.add(rel_path)
            match_item: dict[str, Any] = {
                "path": rel_path,
                "line": line_number,
                "content": _redact_secret_content(line),
            }
            if context:
                before = file_lines[max(0, line_index - context) : line_index]
                after = file_lines[line_index + 1 : line_index + 1 + context]
                match_item["context_before"] = [_redact_secret_content(item) for item in before]
                match_item["context_after"] = [_redact_secret_content(item) for item in after]
            matches.append(match_item)

    if output_mode == "files_only":
        files = sorted(files_with_matches)
        selected_files = files[offset : offset + limit]
        return {
            "target": "content",
            "pattern": pattern,
            "files": selected_files,
            "total_count": len(files),
            "offset": offset,
            "limit": limit,
            "truncated": offset + len(selected_files) < len(files),
        }
    if output_mode == "count":
        ordered = dict(sorted(counts.items()))
        sliced_keys = list(ordered)[offset : offset + limit]
        return {
            "target": "content",
            "pattern": pattern,
            "counts": {key: ordered[key] for key in sliced_keys},
            "total_count": len(ordered),
            "offset": offset,
            "limit": limit,
            "truncated": offset + len(sliced_keys) < len(ordered),
        }
    if output_mode != "content":
        raise ValueError("output_mode must be content, files_only, or count")

    matches.sort(key=lambda item: (item["path"], item["line"]))
    selected = matches[offset : offset + limit]
    return {
        "target": "content",
        "pattern": pattern,
        "matches": selected,
        "total_count": len(matches),
        "offset": offset,
        "limit": limit,
        "truncated": offset + len(selected) < len(matches),
    }


def _iter_files(path: Path, *, root: Path | None = None) -> list[Path]:
    if path.is_file():
        return [path]
    if not path.is_dir():
        raise NotADirectoryError(str(path))

    files: list[Path] = []
    for current_root, dirs, names in os.walk(path):
        walk_root = Path(current_root)
        dirs[:] = [
            name
            for name in dirs
            if name not in SKIPPED_DIRS
        ]
        for name in names:
            file_path = walk_root / name
            files.append(file_path)
    return files


def _redact_secret_content(content: str) -> str:
    """읽기 결과가 모델 컨텍스트에 들어가기 전에 흔한 secret 값을 마스킹한다."""

    def redact_key_value(match: re.Match[str]) -> str:
        prefix = match.group(1)
        quote = match.group(2)
        if quote:
            return f"{prefix}{quote}[REDACTED]{quote}"
        return f"{prefix}[REDACTED]"

    redacted = SECRET_KEY_PATTERN.sub(redact_key_value, content)
    redacted = PRIVATE_KEY_MARKER_PATTERN.sub("[REDACTED PRIVATE KEY]", redacted)
    return LONG_TOKEN_PATTERN.sub("[REDACTED]", redacted)


def _build_diff(original: str, updated: str, rel_path: str) -> str:
    return "".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            updated.splitlines(keepends=True),
            fromfile=f"a/{rel_path}",
            tofile=f"b/{rel_path}",
        )
    )
