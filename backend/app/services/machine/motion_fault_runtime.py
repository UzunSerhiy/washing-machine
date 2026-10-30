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
        # Serialize recovery verification with polling and fault callbacks.
        self._poll_lock = asyncio.Lock()
        self.interval_seconds = interval_seconds
        self._task: asyncio.Task | None = None
        self._recovery_task: asyncio.Task | None = None
        self.recovery_timeout_seconds = 15.0
        self.last_fault: str | None = None
        self.last_poll_error: str | None = None
        self.last_notification_error: str | None = None

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

    async def verify_exclusive(self, verify, *, operator_confirmed_stopped: bool):
        """Run read-only recovery checks without concurrent monitor polling.

        Does NOT clear any fault latch or authorize motion. The machine latch
        remains active throughout this operation.
        """
        async with self._poll_lock:
            return await asyncio.to_thread(
                verify, operator_confirmed_stopped=operator_confirmed_stopped
            )

    async def acknowledge_exclusive(self, recovery, *, operator_confirmed_stopped: bool):
        """Bound HTTP wait, not serial execution; never cancel a live recovery.

        On timeout the verification continues under polling exclusion and the
        machine latch remains active until verification actually succeeds.
        """
        if self._recovery_task is not None and not self._recovery_task.done():
            raise RuntimeError("Recovery verification already in progress")

        async def transaction():
            async with self._poll_lock:
                logger.info("Motion fault recovery verification started")
                try:
                    result = await asyncio.to_thread(
                        recovery.acknowledge,
                        operator_confirmed_stopped=operator_confirmed_stopped,
                    )
                except Exception:
                    logger.exception("Motion fault recovery verification failed")
                    raise
                self._notified = False
                self.last_fault = None
                self.last_poll_error = None
                self.last_notification_error = None
                logger.info("Motion fault recovery acknowledged")
                return result

        task = asyncio.create_task(transaction(), name="motion-fault-recovery")
        self._recovery_task = task

        def finish(completed):
            # Consume late errors after an HTTP timeout; don't silently lose them.
            if completed.cancelled():
                return
            try:
                completed.result()
            except Exception:
                pass  # Already logged by transaction().

        task.add_done_callback(finish)
        try:
            return await asyncio.wait_for(asyncio.shield(task), self.recovery_timeout_seconds)
        except asyncio.TimeoutError as exc:
            logger.error("Recovery still running after %.1fs; keeping serial verification isolated",
                         self.recovery_timeout_seconds)
            raise TimeoutError(
                "Recovery verification still running; do not retry. "
                "Check backend logs and drive communication"
            ) from exc

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(self.interval_seconds)
            try:
                async with self._poll_lock:
                    # Polling and callback must be one serialized operation.
                    await self._poll_once()
                self.last_poll_error = None
            except Exception as exc:
                self.last_poll_error = str(exc)
                logger.exception("Motion fault polling failed")

    async def _poll_once(self) -> None:
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
                except Exception as exc:
                    self.last_notification_error = f"{type(exc).__name__}: {exc}"
                    logger.exception("Motion fault session notification failed")
