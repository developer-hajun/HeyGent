from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path


def _load_srt_booking_module():
    path = Path("app/skills/k-skills/srt-booking/scripts/srt_booking.py")
    spec = importlib.util.spec_from_file_location("srt_booking_script", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


srt_booking = _load_srt_booking_module()


class FakeSrt:
    def __init__(self) -> None:
        self.calls = []

    def search_train(self, *args, **kwargs):
        self.calls.append({"args": args, "kwargs": kwargs})
        return ["sold-out-train"]


def test_srt_search_command_includes_sold_out_trains_for_explanation():
    fake_srt = FakeSrt()
    args = argparse.Namespace(
        command="search",
        departure="부산",
        arrival="수서",
        date="20260522",
        time="160000",
        time_limit="180000",
        limit=5,
    )

    trains = srt_booking._search(fake_srt, args)

    assert trains == ["sold-out-train"]
    assert fake_srt.calls[0]["kwargs"]["available_only"] is False


def test_srt_reserve_search_keeps_available_only_filter():
    fake_srt = FakeSrt()
    args = argparse.Namespace(
        command="reserve",
        departure="부산",
        arrival="수서",
        date="20260522",
        time="160000",
        time_limit="180000",
        limit=5,
    )

    trains = srt_booking._search(fake_srt, args)

    assert trains == ["sold-out-train"]
    assert fake_srt.calls[0]["kwargs"]["available_only"] is True
