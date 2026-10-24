from threading import RLock

from app.services.machine.brush import Brush
from app.services.machine.roller import Roller
from collections.abc import Callable


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
    ) -> None:
        self.brush = brush
        self.roller = roller

        self._roller_lock = RLock()
        self._roller_owner: str | None = None
        self._roller_external_stop_callback: Callable[[], None] | None = None

    @property
    def roller_owner(self) -> str | None:
        with self._roller_lock:
            return self._roller_owner

    def acquire_roller(self, owner: str) -> None:
        if not owner:
            raise ValueError("Roller owner cannot be empty")

        with self._roller_lock:
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
        if self._roller_owner is not None and self._roller_owner != owner:
            raise RuntimeError(f"Roller is reserved by {self._roller_owner}")

    def start_brush(self, frequency_hz: float) -> None:
        self.brush.start(frequency_hz)

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
            self.roller.forward(frequency_hz)

    def start_roller_reverse(
        self,
        frequency_hz: float,
        *,
        owner: str | None = None,
    ) -> None:
        with self._roller_lock:
            self._require_roller_access(owner)
            self.roller.reverse(frequency_hz)

    def stop_roller(
        self,
        *,
        owner: str | None = None,
    ) -> None:
        with self._roller_lock:
            try:
                self.roller.stop()
            except Exception:
                # При неудачном STOP положение неизвестно.
                # Владение валом не освобождаем.
                raise

            if owner != self._roller_owner:
                self._notify_external_roller_stop()

    def stop_roller_coast(self) -> None:
        with self._roller_lock:
            self.roller.stop_coast()
            self._notify_external_roller_stop()

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
                    errors.append(f"{name}: {exc}")

            if roller_stopped:
                self._notify_external_roller_stop()

        if errors:
            raise RuntimeError("Failed to stop drives: " + "; ".join(errors))

    def set_roller_external_stop_callback(
        self,
        callback: Callable[[], None],
    ) -> None:
        with self._roller_lock:
            self._roller_external_stop_callback = callback

    def _notify_external_roller_stop(self) -> None:
        # Вызывается при уже удерживаемом _roller_lock.
        if self._roller_external_stop_callback is not None:
            self._roller_external_stop_callback()
