"""Best-effort periodic GAIN fault polling (not a safety-rated stop)."""

import asyncio
import logging
from contextlib import suppress
from typing import Callable, Protocol

logger = logging.getLogger(__name__)


class FaultMonitoredMachine(Protocol):
    def poll_motion_faults(self) -> str | None: ...


class MotionFaultRuntime:
    def __init__(self, machine: FaultMonitoredMachine, interval_seconds: float = 0.2, on_fault: Callable[[str], None] | None = None):
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        self.machine = machine
        self.on_fault = on_fault
        self._notified = False
        self.interval_seconds = interval_seconds
        self._task: asyncio.Task | None = None
        self.last_fault: str | None = None
        self.last_poll_error: str | None = None

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self) -> None:
        if not self.running:
            self._task = asyncio.create_task(self._run(), name="motion-fault-runtime")

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
            try:
                # Serial Modbus reads are synchronous: never block FastAPI's loop.
                fault = await asyncio.to_thread(self.machine.poll_motion_faults)
                if fault is not None:
                    if self.last_fault != fault:
                        logger.error("Motion fault latched: %s", fault)
                    self.last_fault = fault
                    if not self._notified and self.on_fault is not None:
                        # Notify only after Machine has latched the fault and attempted STOP.
                        # Never retry a partially failing callback automatically.
                        self._notified = True
                        try:
                            self.on_fault(fault)
                        except Exception:
                            logger.exception("Motion fault session notification failed")
                self.last_poll_error = None
            except Exception as exc:
                # Polling failure must be visible; don't silently treat as healthy.
                self.last_poll_error = str(exc)
                logger.exception("Motion fault polling failed")
