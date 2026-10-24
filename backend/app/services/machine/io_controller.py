"""Shared control of ESP32 water/light outputs and physical switch events."""

import logging
import threading
import time

logger = logging.getLogger(__name__)


class MachineIOController:
    DEVICES = ("water", "light")

    def __init__(self, sensor, poll_interval: float = 0.05):
        self.sensor = sensor
        self.poll_interval = poll_interval
        self._stop = threading.Event()
        self._thread = None
        self._command_lock = threading.RLock()
        self._identity = None
        self._baseline = None
        self._ready = False
        self._needs_reset = True

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name="machine-io-controller", daemon=True
        )
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)
        with self._command_lock:
            self._ready = False

    def set_output(self, device: str, enabled: bool):
        if device not in self.DEVICES or type(enabled) is not bool:
            raise ValueError("Invalid output command")
        with self._command_lock:
            snapshot = self.sensor.read_io()
            if (
                not self._ready
                or not snapshot["connected"]
                or not snapshot["watchdog_alive"]
            ):
                raise RuntimeError("ESP32 IO controller is not ready")
            if (snapshot["generation"], snapshot["boot_id"]) != self._identity:
                self._ready = False
                raise RuntimeError("ESP32 IO connection changed")
            self.sensor.set_output(device, enabled)

    def status(self):
        state = self.sensor.read_io()
        with self._command_lock:
            state["io_ready"] = self._ready
        return state

    def _run(self):
        while not self._stop.wait(self.poll_interval):
            try:
                self._tick()
            except (RuntimeError, TimeoutError, ValueError, KeyError) as exc:
                logger.warning("Machine IO controller: %s", exc)
            except Exception:
                logger.exception("Unexpected machine IO controller failure")

    def _tick(self):
        with self._command_lock:
            snapshot = self.sensor.read_io()
            if (
                not snapshot["connected"]
                or not snapshot["watchdog_alive"]
                or snapshot["boot_id"] is None
            ):
                self._ready = False
                self._needs_reset = True
                self._baseline = None
                self._identity = None
                return

            identity = (snapshot["generation"], snapshot["boot_id"])
            if identity != self._identity:
                self._identity = identity
                self._ready = False
                self._needs_reset = True
                self._baseline = None

            if self._needs_reset:
                # Watchdog must be alive before accepting OFF acknowledgements.
                for device in self.DEVICES:
                    self.sensor.set_output(device, False)
                snapshot = self.sensor.read_io()
                if (
                    not snapshot["connected"]
                    or (snapshot["generation"], snapshot["boot_id"]) != identity
                ):
                    return
                self._baseline = {
                    device: (
                        snapshot[f"{device}_switch"],
                        snapshot[f"{device}_switch_changes"],
                    )
                    for device in self.DEVICES
                }
                self._needs_reset = False
                self._ready = True
                logger.info(
                    "Machine IO initialized; outputs OFF, switch positions ignored"
                )
                return

            for device in self.DEVICES:
                position = snapshot[f"{device}_switch"]
                count = snapshot[f"{device}_switch_changes"]
                old_position, old_count = self._baseline[device]
                if count == old_count:
                    continue
                # Ambiguous skipped events or counter reset: resync without actuation.
                if count != old_count + 1 or position == old_position:
                    logger.warning("Ambiguous %s switch event; resynchronizing", device)
                    self._baseline[device] = (position, count)
                    continue
                self._baseline[device] = (position, count)
                self.sensor.set_output(device, position)
                logger.info("Physical %s switch -> %s", device, position)
