import asyncio
import logging

from app.services.machine.roller_homing_service import (
    RollerHomingService,
)


logger = logging.getLogger(__name__)


class RollerHomingRuntime:
    def __init__(
        self,
        homing_service: RollerHomingService,
        interval_seconds: float = 0.1,
    ) -> None:
        self.homing_service = homing_service
        self.interval_seconds = interval_seconds
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        if self._task is not None and not self._task.done():
            return

        self._task = asyncio.create_task(
            self._run(),
            name="roller-homing-runtime",
        )

    async def stop(self) -> None:
        if self._task is None:
            return

        self._task.cancel()

        try:
            await self._task
        except asyncio.CancelledError:
            pass
        finally:
            self._task = None

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(self.interval_seconds)

            try:
                self.homing_service.tick()
            except Exception:
                logger.exception("Roller homing runtime failed")

                # tick() уже пытается остановить вал
                # и фиксирует неисправность.
                # Повторно запускать HOME здесь нельзя.
