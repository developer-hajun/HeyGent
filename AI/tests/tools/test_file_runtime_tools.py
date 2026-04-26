from __future__ import annotations

from pathlib import Path

import pytest

from app.tools.file.file_tools import file_tool_definitions, patch, read_file, search_files, write_file
from app.tools.runtime.local_tool_runtime import LocalToolRuntime


class _DummySessionStore:
    pass


def _args(root: Path, **kwargs):
    return {"workspace_root": str(root), **kwargs}


def test_file_tool_definitions_register_runtime_tool_names():
    definitions = file_tool_definitions()

    assert [item["name"] for item in definitions] == ["read_file", "write_file", "patch", "search_files"]
    assert {item["toolset"] for item in definitions} == {"file"}
    assert definitions[0]["schema"]["name"] == "read_file"
    patch_schema = next(item["schema"] for item in definitions if item["name"] == "patch")
    assert patch_schema["parameters"]["properties"]["mode"]["enum"] == ["replace", "patch"]


def test_read_file_returns_line_numbered_page(tmp_path: Path):
    target = tmp_path / "notes.txt"
    target.write_text("one\ntwo\nthree\n", encoding="utf-8")

    result = read_file(_args(tmp_path, path="notes.txt", offset=2, limit=1))

    assert result["path"] == "notes.txt"
    assert result["content"] == "2|two"
    assert result["total_lines"] == 3
    assert result["returned_lines"] == 1
    assert result["truncated"] is True


def test_read_file_blocks_directory_and_path_escape(tmp_path: Path):
    with pytest.raises(IsADirectoryError):
        read_file(_args(tmp_path, path="."))

    with pytest.raises(PermissionError):
        read_file(_args(tmp_path, path="../outside.txt"))

    with pytest.raises(PermissionError):
        read_file(_args(tmp_path, path=str(tmp_path.parent / "outside.txt")))


def test_write_file_creates_parent_inside_workspace(tmp_path: Path):
    result = write_file(_args(tmp_path, path="nested/result.txt", content="hello\nworld\n"))

    assert result["path"] == "nested/result.txt"
    assert result["dirs_created"] is True
    assert (tmp_path / "nested" / "result.txt").read_text(encoding="utf-8") == "hello\nworld\n"


def test_write_file_blocks_directory_and_path_escape(tmp_path: Path):
    with pytest.raises(IsADirectoryError):
        write_file(_args(tmp_path, path=".", content="blocked"))

    with pytest.raises(PermissionError):
        write_file(_args(tmp_path, path="../outside.txt", content="blocked"))


def test_patch_replace_requires_unique_match_and_updates_file(tmp_path: Path):
    target = tmp_path / "app.py"
    target.write_text("name = 'old'\nprint(name)\n", encoding="utf-8")

    result = patch(
        _args(
            tmp_path,
            mode="replace",
            path="app.py",
            old_string="name = 'old'",
            new_string="name = 'new'",
        )
    )

    assert result["success"] is True
    assert result["files_modified"] == ["app.py"]
    assert "name = 'new'" in target.read_text(encoding="utf-8")
    assert "-name = 'old'" in result["diff"]
    assert "+name = 'new'" in result["diff"]


def test_patch_replace_blocks_ambiguous_match(tmp_path: Path):
    target = tmp_path / "app.py"
    target.write_text("same\nsame\n", encoding="utf-8")

    with pytest.raises(ValueError, match="unique"):
        patch(_args(tmp_path, mode="replace", path="app.py", old_string="same", new_string="other"))


def test_patch_mode_updates_and_adds_files(tmp_path: Path):
    (tmp_path / "app.py").write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
    patch_text = """*** Begin Patch
*** Update File: app.py
@@
 alpha
-beta
+BETA
 gamma
*** Add File: docs/readme.md
+# Title
+body
*** End Patch"""

    result = patch(_args(tmp_path, mode="patch", patch=patch_text))

    assert result["success"] is True
    assert result["mode"] == "patch"
    assert result["files_modified"] == ["app.py"]
    assert result["files_created"] == ["docs/readme.md"]
    assert (tmp_path / "app.py").read_text(encoding="utf-8") == "alpha\nBETA\ngamma\n"
    assert (tmp_path / "docs" / "readme.md").read_text(encoding="utf-8") == "# Title\nbody\n"


def test_patch_apply_patch_alias_is_still_accepted(tmp_path: Path):
    (tmp_path / "app.py").write_text("old\n", encoding="utf-8")
    patch_text = """*** Begin Patch
*** Update File: app.py
@@
-old
+new
*** End Patch"""

    result = patch(_args(tmp_path, mode="apply_patch", patch=patch_text))

    assert result["mode"] == "patch"
    assert (tmp_path / "app.py").read_text(encoding="utf-8") == "new\n"


def test_patch_mode_passes_runtime_validation(tmp_path: Path):
    (tmp_path / "app.py").write_text("old\n", encoding="utf-8")
    patch_text = """*** Begin Patch
*** Update File: app.py
@@
-old
+new
*** End Patch"""
    runtime = LocalToolRuntime(skill_registry=object(), session_store=_DummySessionStore())

    result = runtime.run_call(
        name="patch",
        args={"workspace_root": str(tmp_path), "mode": "patch", "patch": patch_text},
        enabled_toolsets=("file",),
    )

    assert result["success"] is True
    assert (tmp_path / "app.py").read_text(encoding="utf-8") == "new\n"


def test_patch_mode_blocks_outside_workspace(tmp_path: Path):
    patch_text = """*** Begin Patch
*** Add File: ../outside.txt
+blocked
*** End Patch"""

    with pytest.raises(PermissionError):
        patch(_args(tmp_path, mode="patch", patch=patch_text))


def test_patch_mode_multi_file_failure_leaves_no_partial_write(tmp_path: Path):
    target = tmp_path / "app.py"
    target.write_text("alpha\nbeta\n", encoding="utf-8")
    patch_text = """*** Begin Patch
*** Update File: app.py
@@
-beta
+BETA
*** Update File: missing.py
@@
-missing
+MISSING
*** End Patch"""

    with pytest.raises(FileNotFoundError):
        patch(_args(tmp_path, mode="patch", patch=patch_text))

    assert target.read_text(encoding="utf-8") == "alpha\nbeta\n"
    assert not (tmp_path / "missing.py").exists()


def test_patch_mode_moves_file_and_blocks_destination_overwrite(tmp_path: Path):
    source = tmp_path / "src.txt"
    destination = tmp_path / "nested" / "dst.txt"
    source.write_text("content\n", encoding="utf-8")
    patch_text = """*** Begin Patch
*** Move File: src.txt -> nested/dst.txt
*** End Patch"""

    result = patch(_args(tmp_path, mode="patch", patch=patch_text))

    assert result["files_moved"] == [{"from": "src.txt", "to": "nested/dst.txt"}]
    assert not source.exists()
    assert destination.read_text(encoding="utf-8") == "content\n"

    (tmp_path / "next.txt").write_text("next\n", encoding="utf-8")
    overwrite_patch = """*** Begin Patch
*** Move File: next.txt -> nested/dst.txt
*** End Patch"""
    with pytest.raises(FileExistsError):
        patch(_args(tmp_path, mode="patch", patch=overwrite_patch))

    assert (tmp_path / "next.txt").read_text(encoding="utf-8") == "next\n"
    assert destination.read_text(encoding="utf-8") == "content\n"


def test_patch_mode_supports_addition_only_hunk_with_context_hint(tmp_path: Path):
    target = tmp_path / "app.py"
    target.write_text("def run():\n    return 1\n", encoding="utf-8")
    patch_text = """*** Begin Patch
*** Update File: app.py
@@ def run():
+    value = 1
*** End Patch"""

    patch(_args(tmp_path, mode="patch", patch=patch_text))

    assert target.read_text(encoding="utf-8") == "def run():\n    value = 1\n    return 1\n"


def test_search_files_supports_content_pagination_and_file_target(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("needle one\nneedle two\n", encoding="utf-8")
    (tmp_path / "src" / "b.txt").write_text("needle three\n", encoding="utf-8")
    (tmp_path / "src" / "c.py").write_text("nothing\n", encoding="utf-8")

    content_page = search_files(
        _args(tmp_path, path="src", pattern="needle", target="content", file_glob="*.py", offset=1, limit=1)
    )
    file_page = search_files(_args(tmp_path, path="src", pattern="*.py", target="files", offset=0, limit=10))

    assert content_page["total_count"] == 2
    assert content_page["matches"] == [{"path": "src/a.py", "line": 2, "content": "needle two"}]
    assert content_page["truncated"] is False
    assert file_page["files"] == ["src/a.py", "src/c.py"]


def test_search_files_blocks_path_escape_and_skips_binary(tmp_path: Path):
    (tmp_path / "text.txt").write_text("needle\n", encoding="utf-8")
    (tmp_path / "binary.bin").write_bytes(b"needle\x00hidden")

    result = search_files(_args(tmp_path, path=".", pattern="needle", target="content"))

    assert result["total_count"] == 1
    assert result["matches"][0]["path"] == "text.txt"
    with pytest.raises(PermissionError):
        search_files(_args(tmp_path, path="../", pattern="needle", target="content"))
