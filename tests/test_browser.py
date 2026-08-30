from __future__ import annotations

import asyncio

import pytest

from avito_personal_mcp.browser import BrowserAccessGate


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
