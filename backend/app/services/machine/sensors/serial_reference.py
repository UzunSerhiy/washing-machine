import json
import logging
import threading
import time

import serial

from app.services.machine.sensors.roller_reference import RollerReferenceState

logger = logging.getLogger(__name__)


class SerialRollerReferenceSensor:
    def __init__(
        self,
        port: str = "/dev/ttyACM0",
        baudrate: int = 115200,
        timeout: float = 0.5,
    ) -> None:
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout

        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

        self._state = RollerReferenceState(
            connected=False,
            triggered=False,
            pulses=0,
            sequence=0,
        )
        self._last_received = 0.0

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="roller-reference-serial",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def read(self) -> RollerReferenceState:
        with self._lock:
            state = self._state
            last_received = self._last_received

        connected = (
            state.connected
            and time.monotonic() - last_received <= self.timeout
        )

        return RollerReferenceState(
            connected=connected,
            triggered=state.triggered if connected else False,
            pulses=state.pulses,
            sequence=state.sequence,
        )

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                with serial.Serial(
                    self.port,
                    self.baudrate,
                    timeout=0.1,
                ) as connection:
                    logger.info("ESP32 connected: %s", self.port)

                    connection.reset_input_buffer()
                    connection.readline()

                    while not self._stop_event.is_set():
                        raw = connection.readline()

                        if not raw:
                            continue

                        try:
                            message = json.loads(raw)

                            if message.get("type") != "roller_reference":
                                continue

                            triggered = message["triggered"]
                            pulses = message["pulses"]
                            sequence = message["sequence"]

                            if (
                                type(triggered) is not bool
                                or type(pulses) is not int
                                or type(sequence) is not int
                                or pulses < 0
                                or sequence < 0
                            ):
                                continue

                            with self._lock:
                                previous = self._state

                                if (
                                    previous.connected
                                    and sequence <= previous.sequence
                                ):
                                    logger.warning(
                                        "ESP32 sequence reset or repeated"
                                    )
                                    self._state = RollerReferenceState(
                                        connected=False,
                                        triggered=False,
                                        pulses=pulses,
                                        sequence=sequence,
                                    )
                                    self._last_received = 0.0
                                    break

                                self._state = RollerReferenceState(
                                    connected=True,
                                    triggered=triggered,
                                    pulses=pulses,
                                    sequence=sequence,
                                )
                                self._last_received = time.monotonic()

                        except (
                            ValueError,
                            TypeError,
                            KeyError,
                            UnicodeDecodeError,
                        ):
                            logger.warning("Invalid ESP32 serial message")

            except (serial.SerialException, OSError) as exc:
                logger.warning("ESP32 serial unavailable: %s", exc)

            with self._lock:
                self._state = RollerReferenceState(
                    connected=False,
                    triggered=False,
                    pulses=self._state.pulses,
                    sequence=self._state.sequence,
                )
                self._last_received = 0.0

            self._stop_event.wait(1.0)
