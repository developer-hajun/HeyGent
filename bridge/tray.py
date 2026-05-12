"""HeyGent 브릿지 트레이 아이콘 진입점.

bridge/main.py(콘솔 모드)와 같은 일을 하지만, 백그라운드 스레드로 돌리고
시스템 트레이에 H 아이콘과 상태/메뉴를 노출한다.
페어링 안 된 상태에서 시작하면 페어링 코드 입력 모달이 먼저 뜬다.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import threading
from pathlib import Path
from typing import Any

import pystray
from PIL import Image, ImageDraw, ImageFont
from websockets.exceptions import ConnectionClosed


def _asset_path(name: str) -> Path:
    """assets 폴더의 파일 경로를 돌려준다.

    PyInstaller --onefile 로 빌드되면 sys._MEIPASS 임시 폴더 아래에 풀린다.
    개발 중에는 bridge/assets/ 에서 직접 읽는다.
    """

    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base) / "assets" / name
    return Path(__file__).resolve().parent / "assets" / name

from bridge import environments
from bridge.config import BridgeSettings, load_settings
from bridge.main import _run_session
from bridge.pairing import BridgePairingError, request_pair, request_unpair
from bridge.storage import BridgeStoredState, clear_pairing, load_state, save_state


logger = logging.getLogger("bridge.tray")


def _update_env_workspace_root(new_path: Path) -> None:
    """bridge/.env 의 BRIDGE_WORKSPACE_ROOT 항목만 새 경로로 교체한다."""

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


class BridgeTrayApp:
    def __init__(self, settings: BridgeSettings) -> None:
        self.settings = settings
        self.connected = False
        # True 면 main() 의 outer loop 가 다시 페어링 다이얼로그를 띄운다.
        # False 면 사용자가 [종료] 메뉴를 눌러 진짜로 닫고 싶다는 뜻.
        self.unpair_requested = False
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._stop_event: asyncio.Event | None = None
        self.icon = pystray.Icon(
            "heygent-bridge",
            self._render_icon(connected=False),
            "HeyGent 브릿지 (끊김)",
            menu=self._build_menu(),
        )

    # 로고 이미지는 한 번만 로드해서 재사용한다.
    _LOGO_BASE: Image.Image | None = None

    @classmethod
    def _get_logo_base(cls) -> Image.Image | None:
        if cls._LOGO_BASE is not None:
            return cls._LOGO_BASE
        try:
            path = _asset_path("icon.png")
            if not path.exists():
                return None
            cls._LOGO_BASE = Image.open(path).convert("RGBA").resize((64, 64), Image.LANCZOS)
            return cls._LOGO_BASE
        except Exception:
            logger.exception("트레이 로고 이미지 로드 실패")
            return None

    @classmethod
    def _render_icon(cls, *, connected: bool) -> Image.Image:
        size = 64
        base = cls._get_logo_base()
        if base is not None:
            # 로고 위에 작은 상태 점(초록/빨강)을 오버레이해서 연결됨/끊김을 구분한다.
            image = base.copy()
            draw = ImageDraw.Draw(image)
            dot_color = (40, 180, 80, 255) if connected else (200, 50, 50, 255)
            # 오른쪽 아래 모서리에 작은 원.
            r = 12
            x0 = size - r * 2 - 2
            y0 = size - r * 2 - 2
            draw.ellipse((x0, y0, x0 + r * 2, y0 + r * 2), fill=dot_color, outline=(0, 0, 0, 200), width=1)
            return image

        # 로고가 없으면 기존 글자 방식으로 폴백.
        image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        color = (40, 180, 80, 255) if connected else (200, 50, 50, 255)
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

    def _build_menu(self) -> pystray.Menu:
        return pystray.Menu(
            pystray.MenuItem(self._status_label, None, enabled=False),
            pystray.MenuItem(self._user_label, None, enabled=False),
            pystray.MenuItem(self._workspace_label, None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("워크스페이스 열기", self._open_workspace),
            pystray.MenuItem("이 디바이스 페어링 해제", self._unpair_local),
            pystray.MenuItem("종료", self._quit),
        )

    def _status_label(self, _icon: pystray.Icon) -> str:
        env = environments.find(self.settings.environment_key)
        suffix = f" ({env.label})"
        return ("상태: 연결됨" if self.connected else "상태: 끊김") + suffix

    def _user_label(self, _icon: pystray.Icon) -> str:
        if self.settings.device_name and self.settings.user_id:
            return f"사용자: {self.settings.user_id} / {self.settings.device_name}"
        return "사용자: 페어링 안 됨"

    def _workspace_label(self, _icon: pystray.Icon) -> str:
        path = str(self.settings.workspace_root)
        if len(path) > 50:
            path = "…" + path[-47:]
        return f"폴더: {path}"

    def _open_workspace(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        try:
            os.startfile(str(self.settings.workspace_root))  # type: ignore[attr-defined]
        except Exception:
            logger.exception("워크스페이스 열기 실패")

    def _unpair_local(self, icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        """이 PC 의 토큰을 서버에서 폐기하고 로컬 저장 파일도 비운 뒤 프로세스를 종료한다.

        서버 호출이 실패해도 (네트워크 문제 등) 로컬 토큰은 그래도 비운다.
        같은 프로세스 안에서 customtkinter 다이얼로그를 두 번째로 띄우면 tk 리소스 잔재가 남아
        트레이 아이콘이 잔상으로 남는 케이스가 있다. 그래서 해제 직후엔 명시적으로 종료한다.
        안내는 트레이 알림(toast) 으로만 짧게 띄운다 — tkinter messagebox 는 pystray 콜백
        스레드에서 띄우면 응답하지 않는 케이스가 있어서 쓰지 않는다.
        """

        state = load_state()
        token = state.bridge_token
        api_base_url = state.api_base_url or self.settings.api_base_url
        if token and api_base_url:
            try:
                request_unpair(api_base_url=api_base_url, bridge_token=token)
                logger.info("서버에서 디바이스가 폐기되었습니다.")
            except BridgePairingError as exc:
                logger.warning("서버 디바이스 폐기 실패 (로컬 정리는 진행): %s", exc)
        save_state(clear_pairing(state))
        logger.info("로컬 페어링 정보 삭제됨, 종료합니다.")

        # 트레이 토스트 알림으로 안내. 윈도우에서 짧게 표시되고 자동으로 사라진다.
        try:
            icon.notify("페어링이 해제되었습니다. 다시 사용하려면 프로그램을 재실행해 주세요.", "HeyGent 브릿지")
        except Exception:
            logger.exception("트레이 알림 표시 실패")

        self.unpair_requested = False
        self._shutdown(icon)

    def _quit(self, icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        logger.info("트레이 메뉴에서 종료 요청됨")
        self.unpair_requested = False
        self._shutdown(icon)

    def _shutdown(self, icon: pystray.Icon) -> None:
        """비동기 루프와 트레이 아이콘을 같이 정리한다.

        unpair_requested 플래그는 호출 측이 미리 세팅한다. 여기서는 단지 멈추기만 한다.
        icon.visible=False 를 명시해 윈도우 알림 영역에서 아이콘이 즉시 사라지도록 한다.
        """

        try:
            icon.visible = False
        except Exception:
            pass
        if self._loop is not None and self._stop_event is not None:
            self._loop.call_soon_threadsafe(self._stop_event.set)
        icon.stop()

    def _set_connected(self, value: bool) -> None:
        if self.connected == value:
            return
        self.connected = value
        self.icon.icon = self._render_icon(connected=value)
        self.icon.title = "HeyGent 브릿지 (연결됨)" if value else "HeyGent 브릿지 (끊김)"
        try:
            self.icon.update_menu()
        except Exception:
            pass

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
        self.icon.run()
        if self._thread is not None:
            self._thread.join(timeout=5.0)


# ---------- 시작 다이얼로그 ----------


def _show_startup_dialog(settings: BridgeSettings) -> BridgeSettings | None:
    """시작 GUI: 환경 선택 + 워크스페이스 확인 + (페어링 안 됐으면) 페어링 입력.

    [시작] 누르면 최종 settings 반환 (필요 시 새 페어링 토큰 포함). [취소]/X면 None.
    """

    import customtkinter as ctk
    from tkinter import filedialog, messagebox

    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")

    current: dict[str, Any] = {
        "confirmed": False,
        "settings": settings,
    }

    root = ctk.CTk()
    root.title("HeyGent 브릿지")
    # 윈도우 작업표시줄/타이틀바 아이콘을 로고로. .ico 가 없거나 실패하면 조용히 무시.
    try:
        ico_path = _asset_path("icon.ico")
        if ico_path.exists():
            root.iconbitmap(default=str(ico_path))
    except Exception:
        logger.exception("시작 다이얼로그 아이콘 설정 실패")
    root.attributes("-topmost", True)
    width, height = 580, 480
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    root.geometry(f"{width}x{height}+{(screen_w - width) // 2}+{(screen_h - height) // 2}")
    root.resizable(False, False)

    header = ctk.CTkLabel(
        root,
        text="HeyGent 브릿지",
        font=ctk.CTkFont(family="맑은 고딕", size=22, weight="bold"),
    )
    header.pack(pady=(20, 4))

    subtitle = ctk.CTkLabel(
        root,
        text="환경을 선택하고 이 PC 를 HeyGent 계정에 연결하세요.",
        font=ctk.CTkFont(family="맑은 고딕", size=12),
        text_color="#9ca3af",
    )
    subtitle.pack(pady=(0, 14))

    # ── 환경 선택 ──
    env_var = ctk.StringVar(value=settings.environment_key)
    env_frame = ctk.CTkFrame(root, fg_color="transparent")
    env_frame.pack(padx=24, fill="x")
    ctk.CTkLabel(env_frame, text="환경", width=70, anchor="w").pack(side="left")
    for env in environments.ALL:
        ctk.CTkRadioButton(env_frame, text=env.label, variable=env_var, value=env.key).pack(side="left", padx=8)

    # ── 페어링 상태 ──
    pair_status_var = ctk.StringVar(value=_paired_status_text(settings))
    pair_status_label = ctk.CTkLabel(
        root,
        textvariable=pair_status_var,
        font=ctk.CTkFont(family="맑은 고딕", size=12),
        text_color="#22c55e" if settings.is_paired else "#f59e0b",
    )
    pair_status_label.pack(padx=24, anchor="w", pady=(14, 6))

    code_var = ctk.StringVar()
    name_var = ctk.StringVar(value=settings.device_name or "")

    pair_inputs = ctk.CTkFrame(root, fg_color="#1f2937", corner_radius=8)
    pair_inputs.pack(padx=24, fill="x", pady=(0, 6))

    code_row = ctk.CTkFrame(pair_inputs, fg_color="transparent")
    code_row.pack(padx=12, pady=(12, 6), fill="x")
    ctk.CTkLabel(code_row, text="페어링 코드", width=90, anchor="w").pack(side="left")
    code_entry = ctk.CTkEntry(code_row, textvariable=code_var, font=ctk.CTkFont(family="Consolas", size=14), height=32, width=160)
    code_entry.pack(side="left", padx=(6, 0))

    name_row = ctk.CTkFrame(pair_inputs, fg_color="transparent")
    name_row.pack(padx=12, pady=(0, 12), fill="x")
    ctk.CTkLabel(name_row, text="디바이스 이름", width=90, anchor="w").pack(side="left")
    name_entry = ctk.CTkEntry(name_row, textvariable=name_var, height=32)
    name_entry.pack(side="left", padx=(6, 0), fill="x", expand=True)

    pair_message_var = ctk.StringVar(value="")
    pair_message = ctk.CTkLabel(root, textvariable=pair_message_var, text_color="#ef4444", anchor="w")
    pair_message.pack(padx=24, fill="x")

    def _on_pair_click() -> None:
        env = environments.find(env_var.get())
        api_base_url = env.api_base_url
        code = code_var.get().strip()
        device_name = name_var.get().strip()
        if not code or not device_name:
            pair_message_var.set("페어링 코드와 디바이스 이름을 모두 입력하세요.")
            return
        if not code.isdigit() or len(code) != 6:
            pair_message_var.set("페어링 코드는 6자리 숫자여야 합니다.")
            return
        pair_message_var.set("페어링 중…")
        root.update_idletasks()
        try:
            result = request_pair(api_base_url=api_base_url, code=code, device_name=device_name)
        except BridgePairingError as exc:
            pair_message_var.set(str(exc))
            return
        # 저장 후 status 갱신.
        state = load_state()
        state.bridge_token = result.bridge_token
        state.device_id = result.device_id
        state.device_name = result.device_name
        state.user_id = result.user_id
        state.environment = env.key
        state.api_base_url = env.api_base_url
        state.ws_url = env.ws_url
        save_state(state)
        current["settings"] = load_settings()
        pair_message_var.set("")
        pair_status_var.set(_paired_status_text(current["settings"]))
        pair_status_label.configure(text_color="#22c55e")
        messagebox.showinfo("페어링 성공", f"디바이스 '{result.device_name}' 가 연결되었습니다.")

    pair_btn = ctk.CTkButton(
        pair_inputs,
        text="페어링 요청",
        command=_on_pair_click,
        height=32,
        fg_color="#2563eb",
        hover_color="#1d4ed8",
    )
    pair_btn.pack(padx=12, pady=(0, 12))

    # ── 워크스페이스 ──
    workspace_frame = ctk.CTkFrame(root, fg_color="transparent")
    workspace_frame.pack(padx=24, fill="x")
    ctk.CTkLabel(workspace_frame, text="워크스페이스 폴더", width=110, anchor="w").pack(side="left")
    path_var = ctk.StringVar(value=str(settings.workspace_root))
    path_entry = ctk.CTkEntry(workspace_frame, textvariable=path_var, font=ctk.CTkFont(family="Consolas", size=10), height=30)
    path_entry.pack(side="left", padx=(6, 6), fill="x", expand=True)

    def _browse() -> None:
        new = filedialog.askdirectory(title="워크스페이스 폴더 선택", initialdir=path_var.get())
        if new:
            path_var.set(str(Path(new).resolve()))

    ctk.CTkButton(workspace_frame, text="찾기", command=_browse, width=70, height=30, fg_color="#374151", hover_color="#4b5563").pack(side="left")

    # ── 시작/취소 ──
    def _confirm() -> None:
        path = Path(path_var.get()).resolve()
        if not path.exists() or not path.is_dir():
            messagebox.showerror("폴더 없음", f"폴더가 없거나 디렉터리가 아닙니다.\n\n{path}")
            return
        latest = current["settings"]
        if not latest.is_paired:
            messagebox.showerror("페어링 필요", "먼저 페어링 코드를 입력해 토큰을 발급받으세요.")
            return
        # 환경 변경이 있으면 storage 에 반영.
        state = load_state()
        chosen_env = environments.find(env_var.get())
        if state.environment != chosen_env.key or state.api_base_url != chosen_env.api_base_url or state.ws_url != chosen_env.ws_url:
            state.environment = chosen_env.key
            state.api_base_url = chosen_env.api_base_url
            state.ws_url = chosen_env.ws_url
            save_state(state)
        if path != latest.workspace_root:
            _update_env_workspace_root(path)
        current["settings"] = load_settings()
        current["confirmed"] = True
        root.destroy()

    def _cancel() -> None:
        current["confirmed"] = False
        root.destroy()

    button_frame = ctk.CTkFrame(root, fg_color="transparent")
    button_frame.pack(pady=20)

    ctk.CTkButton(button_frame, text="시작", command=_confirm, width=132, height=40,
                  font=ctk.CTkFont(family="맑은 고딕", size=13, weight="bold"),
                  fg_color="#22c55e", hover_color="#16a34a").pack(side="left", padx=6)
    ctk.CTkButton(button_frame, text="취소", command=_cancel, width=132, height=40,
                  font=ctk.CTkFont(family="맑은 고딕", size=13),
                  fg_color="#374151", hover_color="#4b5563").pack(side="left", padx=6)

    root.protocol("WM_DELETE_WINDOW", _cancel)
    root.mainloop()

    # mainloop 가 destroy 후에도 tk 리소스가 남아 있는 경우 트레이 등록이 미세하게 지연될 수 있어서
    # 명시적으로 quit() 을 한 번 더 부르고 리소스를 푼다.
    try:
        root.quit()
    except Exception:
        pass

    if not current["confirmed"]:
        return None
    return current["settings"]


def _paired_status_text(settings: BridgeSettings) -> str:
    if settings.is_paired and settings.device_name:
        return f"페어링 완료 — user_id={settings.user_id} / device='{settings.device_name}'"
    return "아직 페어링되지 않았습니다. 아래에 6자리 코드와 디바이스 이름을 입력하세요."


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logging.getLogger("websockets").setLevel(logging.INFO)

    # 단일 사이클: 다이얼로그(필요 시) → 트레이 → 종료.
    # 트레이 메뉴 "페어링 해제" 또는 "종료" 는 모두 프로세스를 끝낸다.
    # 같은 프로세스 안에서 customtkinter / pystray 를 재초기화하면 잔상이 남아 안전하지 않다.
    settings = load_settings()
    if not settings.is_paired:
        chosen = _show_startup_dialog(settings)
        if chosen is None:
            logger.info("사용자가 시작을 취소했습니다.")
            return 0
        settings = chosen

    app = BridgeTrayApp(settings)
    try:
        app.run()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
