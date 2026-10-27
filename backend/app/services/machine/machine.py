from threading import RLock

from app.services.machine.brush import Brush
from app.services.machine.roller import Roller
from collections.abc import Callable

from app.services.machine.motion_preflight import require_motion_fault_free


class Machine:
    """
    Единая точка управления исполнительными механизмами.

    Блокировка roller действует для команд,
    проходящих через Machine.
    """

    def __init__(
        self,
        brush: Brush,
        roller: Roller,
        *,
        enforce_motion_preflight: bool = False,
        motion_fault_store=None,
    ) -> None:
        self.brush = brush
        self.roller = roller
        self._enforce_motion_preflight = enforce_motion_preflight

        self._roller_lock = RLock()
        self._roller_owner: str | None = None
        self._external_stop_pending = 0
        self._roller_stop_fault = False
        self._motion_fault_store = motion_fault_store
        self._motion_fault_latched: str | None = (
            motion_fault_store.read_latch() if motion_fault_store is not None else None
        )
        self._roller_external_stop_callback: Callable[[], None] | None = None

    def arm_startup_interlock(self) -> None:
        """REAL startup: require a fresh operator acknowledgement on every boot.

        Persist the interlock before the API can serve motion commands. If the
        storage write fails, startup must fail rather than expose a clean latch.
        """
        if self._motion_fault_store is None:
            return
        with self._roller_lock:
            if self._motion_fault_latched is None:
                self._motion_fault_latched = "Motion blocked: backend restarted; operator acknowledgement required"
            try:
                self._motion_fault_store.write_latch(self._motion_fault_latched)
            except Exception as exc:
                raise RuntimeError("Cannot persist startup motion interlock; refusing startup") from exc

    @property
    def roller_owner(self) -> str | None:
        with self._roller_lock:
            return self._roller_owner

    def acquire_roller(self, owner: str) -> None:
        if not owner:
            raise ValueError("Roller owner cannot be empty")

        with self._roller_lock:
            if self._motion_fault_latched is not None:
                raise RuntimeError("Motion fault is latched")
            if self._roller_stop_fault:
                raise RuntimeError("Roller STOP fault is latched")
            if self._external_stop_pending:
                raise RuntimeError("Roller external STOP notification is pending")
            if self._roller_owner is not None:
                raise RuntimeError(f"Roller is reserved by {self._roller_owner}")

            self._roller_owner = owner

    def release_roller(self, owner: str) -> None:
        with self._roller_lock:
            if self._roller_owner != owner:
                raise RuntimeError("Roller ownership mismatch")

            self._roller_owner = None

    def _require_roller_access(
        self,
        owner: str | None,
    ) -> None:
        if self._roller_stop_fault:
            raise RuntimeError("Roller STOP fault is latched")
        if self._external_stop_pending:
            raise RuntimeError("Roller external STOP notification is pending")
        if self._roller_owner is not None and self._roller_owner != owner:
            raise RuntimeError(f"Roller is reserved by {self._roller_owner}")

    @property
    def motion_fault_latched(self) -> str | None:
        """Diagnostic latch; physical RESET does not clear this state."""
        with self._roller_lock:
            return self._motion_fault_latched

    def poll_motion_faults(self) -> str | None:
        """One explicit monitoring iteration; caller must schedule polling.

        A detected fault is latched before best-effort STOP. This is not a
        hard real-time safety mechanism and does not replace a wired E-stop.
        """
        if not self._enforce_motion_preflight:
            return None
        with self._roller_lock:
            if self._motion_fault_latched is not None:
                return self._motion_fault_latched
            try:
                require_motion_fault_free((
                    ("left_brush", self.brush.left_drive),
                    ("right_brush", self.brush.right_drive),
                    ("roller", self.roller.drive),
                ))
            except Exception as exc:
                self._motion_fault_latched = str(exc)
                if self._motion_fault_store is not None:
                    try:
                        self._motion_fault_store.write_latch(self._motion_fault_latched)
                    except OSError:
                        # Never clear the in-memory latch if persistence fails.
                        pass
            else:
                return None
        try:
            self.stop_all()
        except Exception:
            # Preserve the original fault; failed STOP is separately latched.
            pass
        return self.motion_fault_latched

    def complete_motion_fault_recovery(self) -> None:
        """Clear only the global software latch; caller holds recovery lock."""
        with self._roller_lock:
            if self._roller_owner is not None or self._roller_stop_fault or self._external_stop_pending:
                raise RuntimeError("Roller ownership/STOP fault still active")
            if self._motion_fault_store is not None:
                try:
                    self._motion_fault_store.write_latch(None)
                except OSError as exc:
                    raise RuntimeError("Cannot persist motion fault acknowledgement") from exc
            self._motion_fault_latched = None

    def _check_motion_preflight(self) -> None:
        if self._motion_fault_latched is not None:
            raise RuntimeError(f"Motion fault latched: {self._motion_fault_latched}")
        if self._enforce_motion_preflight:
            require_motion_fault_free((
                ("left_brush", self.brush.left_drive),
                ("right_brush", self.brush.right_drive),
                ("roller", self.roller.drive),
            ))

    def _execute_motion(self, command: Callable[[], None]) -> None:
        """Latch a failed motion dispatch before best-effort STOP (REAL only).

        Validation and ownership errors are deliberately outside this helper.
        """
        with self._roller_lock:
            # An existing latch is not a new fault; never dispatch or clear it.
            if self._motion_fault_latched is not None:
                raise RuntimeError(f"Motion fault latched: {self._motion_fault_latched}")
            try:
                # A failed preflight is itself a machine-level fault in REAL:
                # persist it and attempt STOP, just like a failed RUN dispatch.
                self._check_motion_preflight()
                command()
            except Exception as exc:
                if not self._enforce_motion_preflight:
                    raise
                self._motion_fault_latched = f"Motion command failed: {exc}"
                if self._motion_fault_store is not None:
                    try:
                        self._motion_fault_store.write_latch(self._motion_fault_latched)
                    except Exception:
                        # An in-memory latch remains active; never mask original failure.
                        pass
                try:
                    self.stop_all()
                except Exception:
                    # STOP is best effort, not evidence of physical standstill.
                    pass
                raise

    def start_brush(self, frequency_hz: float) -> None:
        self._execute_motion(lambda: self.brush.start(frequency_hz))

    def stop_brush(self) -> None:
        self.brush.stop()

    def start_roller_forward(
        self,
        frequency_hz: float,
        *,
        owner: str | None = None,
    ) -> None:
        with self._roller_lock:
            self._require_roller_access(owner)
            self._execute_motion(lambda: self.roller.forward(frequency_hz))

    def start_roller_reverse(
        self,
        frequency_hz: float,
        *,
        owner: str | None = None,
    ) -> None:
        with self._roller_lock:
            self._require_roller_access(owner)
            self._execute_motion(lambda: self.roller.reverse(frequency_hz))

    def stop_roller(
        self,
        *,
        owner: str | None = None,
    ) -> None:
        with self._roller_lock:
            try:
                self.roller.stop()
            except Exception:
                # An unsuccessful STOP cannot be treated as safe.
                self._roller_stop_fault = True
                raise

            notify_external = owner != self._roller_owner
            if notify_external:
                self._external_stop_pending += 1

        if notify_external:
            try:
                self._notify_external_roller_stop()
            except Exception:
                with self._roller_lock:
                    self._roller_stop_fault = True
                raise
            finally:
                with self._roller_lock:
                    self._external_stop_pending -= 1

    def stop_roller_coast(self) -> None:
        with self._roller_lock:
            try:
                self.roller.stop_coast()
            except Exception:
                self._roller_stop_fault = True
                raise
            self._external_stop_pending += 1
        try:
            self._notify_external_roller_stop()
        finally:
            with self._roller_lock:
                self._external_stop_pending -= 1

    def stop_all(self) -> None:
        errors = []

        with self._roller_lock:
            drives = (
                ("left_brush", self.brush.left_drive),
                ("right_brush", self.brush.right_drive),
                ("roller", self.roller.drive),
            )

            roller_stopped = False

            for name, drive in drives:
                try:
                    drive.stop()
                    if name == "roller":
                        roller_stopped = True
                except Exception as exc:
                    if name == "roller":
                        self._roller_stop_fault = True
                    errors.append(f"{name}: {exc}")

            if roller_stopped:
                self._external_stop_pending += 1

        if roller_stopped:
            try:
                self._notify_external_roller_stop()
            except Exception:
                with self._roller_lock:
                    self._roller_stop_fault = True
                raise
            finally:
                with self._roller_lock:
                    self._external_stop_pending -= 1

        if errors:
            raise RuntimeError("Failed to stop drives: " + "; ".join(errors))

    def set_roller_external_stop_callback(
        self,
        callback: Callable[[], None],
    ) -> None:
        with self._roller_lock:
            self._roller_external_stop_callback = callback

    def _notify_external_roller_stop(self) -> None:
        with self._roller_lock:
            callback = self._roller_external_stop_callback
        if callback is not None:
            callback()
