import asyncio
import time

from contextlib import suppress
from typing import Protocol


class AutoService(Protocol):
    def tick(self, elapsed_seconds: float) -> None: ...


class AutoRuntime:
    def __init__(
        self,
        auto_service: AutoService,
        interval_seconds: float = 0.1,
    ):
        if interval_seconds <= 0:
            raise ValueError("Interval must be greater than zero")

        self.auto_service = auto_service
        self.interval_seconds = interval_seconds

        self._task: asyncio.Task | None = None

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self) -> None:
        if self.running:
            return

        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task is None:
            return

        self._task.cancel()

        with suppress(asyncio.CancelledError):
            await self._task

        self._task = None

    async def _run(self) -> None:
        last_tick = time.monotonic()

        while True:
            await asyncio.sleep(self.interval_seconds)

            now = time.monotonic()
            elapsed_seconds = now - last_tick
            last_tick = now

            self.auto_service.tick(elapsed_seconds=elapsed_seconds)
