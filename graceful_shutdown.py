# graceful_shutdown.py
from __future__ import annotations
import asyncio
import signal
from typing import Optional, Callable

def install_signal_handlers(loop: asyncio.AbstractEventLoop) -> asyncio.Event:
    """
    Tạo Event stop() khi nhận SIGINT/SIGTERM. Dùng cho while-loop chính.
    """
    stop_event = asyncio.Event()

    def _handler():
        if not stop_event.is_set():
            stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handler)
        except NotImplementedError:
            # Windows/limited env: fallback
            pass
    return stop_event

async def cancel_all_tasks(grace: float = 5.0):
    """
    Hủy tất cả task còn lại để thoát nhanh.
    """
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for t in tasks:
        t.cancel()
    if tasks:
        try:
            await asyncio.wait(tasks, timeout=grace)
        except Exception:
            pass
