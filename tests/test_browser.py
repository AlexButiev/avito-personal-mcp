from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from avito_personal_mcp import browser as browser_module
from avito_personal_mcp.browser import BrowserAccessGate, connect_to_chrome


def test_browser_access_gate_rejects_negative_interval() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        BrowserAccessGate(-0.1)


@pytest.mark.asyncio
async def test_browser_access_gate_serializes_callers() -> None:
    gate = BrowserAccessGate(0)
    order: list[str] = []
    first_entered = asyncio.Event()
    allow_first_to_leave = asyncio.Event()

    async def first() -> None:
        await gate.acquire()
        order.append("first-enter")
        first_entered.set()
        await allow_first_to_leave.wait()
        order.append("first-leave")
        gate.release()

    async def second() -> None:
        await first_entered.wait()
        await gate.acquire()
        order.append("second-enter")
        gate.release()

    first_task = asyncio.create_task(first())
    second_task = asyncio.create_task(second())

    await first_entered.wait()
    await asyncio.sleep(0)
    assert order == ["first-enter"]

    allow_first_to_leave.set()
    await asyncio.gather(first_task, second_task)

    assert order == ["first-enter", "first-leave", "second-enter"]


@pytest.mark.asyncio
async def test_browser_access_gate_applies_minimum_start_interval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate = BrowserAccessGate(0.25)
    monotonic_values = iter([10.0, 10.0, 10.1, 10.35])
    sleeps: list[float] = []

    monkeypatch.setattr(
        "avito_personal_mcp.browser.monotonic",
        lambda: next(monotonic_values),
    )

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    monkeypatch.setattr("avito_personal_mcp.browser.asyncio.sleep", fake_sleep)

    await gate.acquire()
    gate.release()
    await gate.acquire()
    gate.release()

    assert sleeps == pytest.approx([0.15])


def test_browser_access_gate_rejects_double_release() -> None:
    gate = BrowserAccessGate(0)

    with pytest.raises(RuntimeError, match="not acquired"):
        gate.release()


@pytest.mark.asyncio
async def test_connect_failure_releases_gate_even_if_playwright_stop_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate = BrowserAccessGate(0)

    class FakeChromium:
        async def connect_over_cdp(self, cdp_url: str) -> None:
            raise RuntimeError("connect failed")

    class FakePlaywright:
        chromium = FakeChromium()

        async def stop(self) -> None:
            raise RuntimeError("stop failed")

    class FakeStarter:
        async def start(self) -> FakePlaywright:
            return FakePlaywright()

    monkeypatch.setattr(browser_module, "_BROWSER_ACCESS", gate)
    monkeypatch.setattr(browser_module, "async_playwright", lambda: FakeStarter())

    settings = SimpleNamespace(cdp_url="http://127.0.0.1:9222")

    with pytest.raises(RuntimeError, match="stop failed"):
        await connect_to_chrome(settings)  # type: ignore[arg-type]

    await gate.acquire()
    gate.release()
