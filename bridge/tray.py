"""HeyGent 브릿지 트레이 아이콘 진입점.

bridge/main.py(콘솔 모드)와 같은 일을 하지만, 백그라운드 스레드로 돌리고
시스템 트레이에 H 아이콘과 상태/메뉴를 노출한다.
"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

import pystray
from PIL import Image, ImageDraw, ImageFont
from websockets.exceptions import ConnectionClosed

from bridge.config import BridgeSettings, load_settings
from bridge.main import _run_session


logger = logging.getLogger("bridge.tray")


def _update_env_workspace_root(new_path: Path) -> None:
    """bridge/.env 의 BRIDGE_WORKSPACE_ROOT 항목만 새 경로로 교체한다.

    다른 키(BRIDGE_TOKEN 등)와 주석은 그대로 보존한다.
    파일이 없으면 새로 만든다.
    """

    env_file = Path(__file__).resolve().parent / ".env"
    new_value = str(new_path)
    new_line = f"BRIDGE_WORKSPACE_ROOT={new_value}"

    if not env_file.exists():
        env_file.write_text(new_line + "\n", encoding="utf-8")
        return

    lines = env_file.read_text(encoding="utf-8").splitlines()
    replaced = False
    for index, raw in enumerate(lines):
        stripped = raw.strip()
        if stripped.startswith("#") or "=" not in stripped:
            continue
        key, _ = stripped.split("=", 1)
        if key.strip() == "BRIDGE_WORKSPACE_ROOT":
            lines[index] = new_line
            replaced = True
            break
    if not replaced:
        lines.append(new_line)
    env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


# 트레이 아이콘은 별도 스레드의 asyncio 루프에서 굴리고,
# 메인 스레드는 pystray 이벤트 루프(블로킹)를 잡고 있어야 한다.
class BridgeTrayApp:
    def __init__(self, settings: BridgeSettings) -> None:
        self.settings = settings
        self.connected = False
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._stop_event: asyncio.Event | None = None
        self.icon = pystray.Icon(
            "heygent-bridge",
            self._render_icon(connected=False),
            "HeyGent 브릿지 (끊김)",
            menu=self._build_menu(),
        )

    # ---------- 아이콘 그리기 ----------
    @staticmethod
    def _render_icon(*, connected: bool) -> Image.Image:
        size = 64
        # 배경 투명, H 글자만 색으로 표시.
        image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        color = (40, 180, 80, 255) if connected else (200, 50, 50, 255)
        # 환경별로 폰트 다름 — 시스템 기본 폰트 사용 시도, 실패 시 default.
        try:
            font = ImageFont.truetype("arialbd.ttf", 52)
        except OSError:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), "H", font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        x = (size - text_w) // 2 - bbox[0]
        y = (size - text_h) // 2 - bbox[1]
        draw.text((x, y), "H", font=font, fill=color)
        return image

    # ---------- 메뉴 ----------
    def _build_menu(self) -> pystray.Menu:
        # 워크스페이스 변경은 시작 시 다이얼로그에서만 가능.
        # 굴러가는 동안엔 안 바뀜(트레이 종료 → 다시 시작 → 시작 다이얼로그에서 변경).
        return pystray.Menu(
            pystray.MenuItem(self._status_label, None, enabled=False),
            pystray.MenuItem(self._workspace_label, None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("워크스페이스 열기", self._open_workspace),
            pystray.MenuItem("종료", self._quit),
        )

    def _status_label(self, _icon: pystray.Icon) -> str:
        return "상태: 연결됨" if self.connected else "상태: 끊김"

    def _workspace_label(self, _icon: pystray.Icon) -> str:
        path = str(self.settings.workspace_root)
        # 너무 길면 끝부분만 보여 메뉴가 화면 밖으로 안 나가게 한다.
        if len(path) > 50:
            path = "…" + path[-47:]
        return f"폴더: {path}"

    def _open_workspace(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        try:
            os.startfile(str(self.settings.workspace_root))  # type: ignore[attr-defined]
        except Exception:
            logger.exception("워크스페이스 열기 실패")

    def _quit(self, icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        logger.info("트레이 메뉴에서 종료 요청됨")
        # 비동기 루프에 종료 신호 보내고 트레이도 닫는다.
        if self._loop is not None and self._stop_event is not None:
            self._loop.call_soon_threadsafe(self._stop_event.set)
        icon.stop()

    # ---------- 상태 갱신 ----------
    def _set_connected(self, value: bool) -> None:
        if self.connected == value:
            return
        self.connected = value
        self.icon.icon = self._render_icon(connected=value)
        self.icon.title = "HeyGent 브릿지 (연결됨)" if value else "HeyGent 브릿지 (끊김)"
        # 메뉴 다시 그리기 위해 update_menu 호출.
        try:
            self.icon.update_menu()
        except Exception:
            pass

    # ---------- 비동기 루프 ----------
    async def _run_forever(self) -> None:
        self._stop_event = asyncio.Event()
        while not self._stop_event.is_set():
            try:
                await _run_session(
                    self.settings,
                    on_connected=lambda: self._set_connected(True),
                    on_disconnected=lambda: self._set_connected(False),
                )
            except (ConnectionClosed, OSError) as exc:
                logger.warning("연결 끊김: %s", exc)
            except Exception:
                logger.exception("세션 처리 중 예외")

            self._set_connected(False)
            if self._stop_event.is_set():
                break

            logger.info("%.1f초 후 재연결합니다.", self.settings.reconnect_delay_seconds)
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.settings.reconnect_delay_seconds)
            except asyncio.TimeoutError:
                pass

    def _thread_target(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._run_forever())
        finally:
            self._loop.close()

    def run(self) -> None:
        self._thread = threading.Thread(target=self._thread_target, name="bridge-async", daemon=True)
        self._thread.start()
        # icon.run()은 메인 스레드를 점유하는 블로킹 호출.
        self.icon.run()
        # 트레이 종료 후 비동기 루프도 정리.
        if self._thread is not None:
            self._thread.join(timeout=5.0)


def _show_startup_dialog(initial_path: Path) -> Path | None:
    """트레이 진입 전 모던 GUI 창을 띄워 워크스페이스 폴더를 확인/변경한다.

    customtkinter 기반. [시작] 누르면 최종 경로 반환, [취소]/X면 None.
    """

    import customtkinter as ctk
    from tkinter import filedialog, messagebox

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    chosen: dict[str, Path | bool | None] = {"path": initial_path, "confirmed": False}

    root = ctk.CTk()
    root.title("HeyGent 브릿지")
    root.attributes("-topmost", True)
    width, height = 540, 260
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    root.geometry(f"{width}x{height}+{(screen_w - width) // 2}+{(screen_h - height) // 2}")
    root.resizable(False, False)

    # ── 헤더 ──
    header = ctk.CTkLabel(
        root,
        text="HeyGent 브릿지",
        font=ctk.CTkFont(family="맑은 고딕", size=22, weight="bold"),
    )
    header.pack(pady=(22, 4))

    subtitle = ctk.CTkLabel(
        root,
        text="이 PC에서 도구가 실행될 폴더를 확인하세요.",
        font=ctk.CTkFont(family="맑은 고딕", size=12),
        text_color="#9ca3af",
    )
    subtitle.pack(pady=(0, 18))

    # ── 폴더 입력 ──
    path_var = ctk.StringVar(value=str(initial_path))
    path_frame = ctk.CTkFrame(root, fg_color="transparent")
    path_frame.pack(padx=24, fill="x")

    path_entry = ctk.CTkEntry(
        path_frame,
        textvariable=path_var,
        font=ctk.CTkFont(family="Consolas", size=11),
        height=36,
    )
    path_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

    def _browse() -> None:
        new = filedialog.askdirectory(title="워크스페이스 폴더 선택", initialdir=path_var.get())
        if new:
            path_var.set(str(Path(new).resolve()))

    browse_btn = ctk.CTkButton(
        path_frame,
        text="폴더 찾기",
        command=_browse,
        width=92,
        height=36,
        fg_color="#374151",
        hover_color="#4b5563",
    )
    browse_btn.pack(side="left")

    # ── 버튼 ──
    def _confirm() -> None:
        path = Path(path_var.get()).resolve()
        if not path.exists() or not path.is_dir():
            messagebox.showerror("폴더 없음", f"폴더가 없거나 디렉터리가 아닙니다.\n\n{path}")
            return
        chosen["path"] = path
        chosen["confirmed"] = True
        root.destroy()

    def _cancel() -> None:
        chosen["confirmed"] = False
        root.destroy()

    button_frame = ctk.CTkFrame(root, fg_color="transparent")
    button_frame.pack(pady=24)

    start_btn = ctk.CTkButton(
        button_frame,
        text="시작",
        command=_confirm,
        width=132,
        height=40,
        font=ctk.CTkFont(family="맑은 고딕", size=13, weight="bold"),
        fg_color="#22c55e",
        hover_color="#16a34a",
    )
    start_btn.pack(side="left", padx=6)

    cancel_btn = ctk.CTkButton(
        button_frame,
        text="취소",
        command=_cancel,
        width=132,
        height=40,
        font=ctk.CTkFont(family="맑은 고딕", size=13),
        fg_color="#374151",
        hover_color="#4b5563",
    )
    cancel_btn.pack(side="left", padx=6)

    root.protocol("WM_DELETE_WINDOW", _cancel)
    root.mainloop()

    if not chosen["confirmed"]:
        return None
    return chosen["path"]  # type: ignore[return-value]


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logging.getLogger("websockets").setLevel(logging.INFO)

    settings = load_settings()
    chosen_path = _show_startup_dialog(settings.workspace_root)
    if chosen_path is None:
        logger.info("사용자가 시작을 취소했습니다.")
        return 0

    # 사용자가 폴더를 바꿨으면 .env에 반영하고 settings도 새로 로드한다.
    if chosen_path != settings.workspace_root:
        _update_env_workspace_root(chosen_path)
        settings = load_settings()
        logger.info("워크스페이스를 변경했습니다: %s", settings.workspace_root)

    app = BridgeTrayApp(settings)
    try:
        app.run()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
