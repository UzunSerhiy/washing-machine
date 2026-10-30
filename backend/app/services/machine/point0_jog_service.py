"""Bounded Point0 positioning pulses with exclusive roller ownership.

This is a service operation, independent of the selected UI mode.
A software timeout is not a hardware safety function.
"""
import math
import threading
from threading import RLock

from app.services.machine.calibration.stop_confirmation import observe_drive_stop


class Point0JogService:
    OWNER = 'point0'
    PULSE_SECONDS = 2.0

    def __init__(self, machine):
        self.machine = machine
        self._lock = RLock()
        self._timer = None
        self._active = False
        self._stopping = False
        self._confirmations = 0
        self._error = None
        self._stop_failed = False
        self._generation = None

    def status(self):
        with self._lock:
            if self._stopping:
                self._poll_stop()
            return {
                'active': self._active, 'stopping': self._stopping,
                'owner': self.machine.roller_owner, 'error': self._error,
                'pulse_seconds': self.PULSE_SECONDS,
            }

    def start(self, direction: str, frequency_hz: float):
        with self._lock:
            if direction not in ('forward', 'reverse'):
                raise ValueError('Invalid direction')
            if isinstance(frequency_hz, bool) or not isinstance(frequency_hz, (int, float)) or not math.isfinite(frequency_hz) or not (1 <= frequency_hz <= 10):
                raise ValueError('Point0 positioning frequency must be 1–10 Hz')
            if self._active or self._stopping or self.machine.roller_owner is not None:
                raise RuntimeError('Roller is already reserved; finish STOP first')
            self.machine.acquire_roller(self.OWNER)
            self._active = True
            self._error = None
            self._stop_failed = False
            self._confirmations = 0
            try:
                self._generation = self.machine.capture_session_generation()
                method = self.machine.start_roller_forward if direction == 'forward' else self.machine.start_roller_reverse
                method(float(frequency_hz), owner=self.OWNER, session_generation=self._generation)
                self._timer = threading.Timer(self.PULSE_SECONDS, self._timeout_stop)
                self._timer.daemon = True
                self._timer.start()
            except Exception:
                # Motion may have been sent; never release ownership on an uncertain start.
                self._request_stop()
                raise
            return self.status()

    def _timeout_stop(self):
        with self._lock:
            self._request_stop()

    def _request_stop(self):
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None
        if not self._active and not self._stopping:
            return
        self._stopping = True
        try:
            self.machine.stop_roller(owner=self.OWNER)
        except Exception as exc:
            self._error = f'Point0 STOP failed: {exc}'
            self._stop_failed = True
            # Keep roller ownership locked until explicit recovery.
        self._active = False

    def stop(self):
        with self._lock:
            self._request_stop()
            return self.status()

    def _poll_stop(self):
        if self._stop_failed:
            return
        try:
            observation = observe_drive_stop(self.machine.roller.drive)
        except Exception as exc:
            self._error = str(exc)
            return
        self._error = None
        self._confirmations = self._confirmations + 1 if observation.confirmed else 0
        if self._confirmations >= 3:
            self._stopping = False
            self._generation = None
            self.machine.release_roller(self.OWNER)
