import asyncio
from contextlib import suppress
from typing import Protocol


class AutoService(Protocol):
    def tick(self) -> None: ...


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
        while True:
            await asyncio.sleep(self.interval_seconds)

            self.auto_service.tick()
