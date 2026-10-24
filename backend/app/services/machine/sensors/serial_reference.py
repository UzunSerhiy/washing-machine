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
        self._state_changed = threading.Condition(self._lock)
        self._command_lock = threading.Lock()
        self._stop_event = threading.Event()

        self._thread: threading.Thread | None = None
        self._generation = 0
        self._boot_id: int | None = None
        self._last_received = 0.0
        self._connection: serial.Serial | None = None
        self._last_ping_sent = 0.0

        self._io_state = {
            "connected": False,
            "watchdog_alive": False,
            "water_switch": False,
            "light_switch": False,
            "water_switch_changes": 0,
            "light_switch_changes": 0,
            "water_output": False,
            "light_output": False,
        }

        self._state = RollerReferenceState(
            connected=False,
            triggered=False,
            pulses=0,
            sequence=0,
            generation=0,
        )

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

            if (
                state.connected
                and time.monotonic() - self._last_received > self.timeout
            ):
                self._generation += 1

                logger.warning(
                    "ESP32 communication timeout, generation=%s",
                    self._generation,
                )

                self._state = RollerReferenceState(
                    connected=False,
                    triggered=False,
                    pulses=state.pulses,
                    sequence=state.sequence,
                    generation=self._generation,
                )
                self._last_received = 0.0

            return self._state

    def read_io(self) -> dict:
        with self._lock:
            result = self._io_state.copy()
            result["connected"] = self._state.connected
            result["generation"] = self._state.generation
            result["boot_id"] = self._boot_id
            return result

    def send_command(self, command: str) -> None:
        if not command or "\n" in command or "\r" in command:
            raise ValueError("Invalid ESP32 command")

        with self._lock:
            connection = self._connection

            if (
                connection is None
                or not connection.is_open
                or not self._state.connected
            ):
                raise RuntimeError("ESP32 is not connected")

            payload = (command + "\n").encode("ascii")

            written = connection.write(payload)
            connection.flush()

            if written != len(payload):
                raise RuntimeError("Incomplete ESP32 command write")

    def set_output(self, device: str, enabled: bool) -> None:
        commands = {
            "water": "SET_WATER",
            "light": "SET_LIGHT",
        }

        if device not in commands:
            raise ValueError(f"Unknown output: {device}")

        if type(enabled) is not bool:
            raise ValueError("Output value must be boolean")

        field = f"{device}_output"
        command = f"{commands[device]} {int(enabled)}"

        with self._command_lock:
            with self._lock:
                if not self._state.connected:
                    raise RuntimeError("ESP32 is not connected")

                initial_sequence = self._state.sequence
                initial_generation = self._state.generation

            self.send_command(command)

            deadline = time.monotonic() + 2.0

            with self._state_changed:
                while True:
                    state = self._state

                    if not state.connected:
                        raise RuntimeError("ESP32 disconnected while waiting for ACK")

                    if state.generation != initial_generation:
                        raise RuntimeError(
                            "ESP32 connection changed while waiting for ACK"
                        )

                    if (
                        state.sequence > initial_sequence
                        and self._io_state[field] is enabled
                    ):
                        logger.info(
                            "ESP32 ACK: %s=%s, sequence=%s",
                            device,
                            enabled,
                            state.sequence,
                        )
                        return

                    remaining = deadline - time.monotonic()

                    if remaining <= 0:
                        raise TimeoutError(f"ESP32 ACK timeout: {device}={enabled}")

                    self._state_changed.wait(timeout=remaining)

    def send_test_pause(self, duration_ms: int) -> None:
        if not 100 <= duration_ms <= 10000:
            raise ValueError("Duration must be between 100 and 10000 ms")

        with self._lock:
            connection = self._connection

            if connection is None or not connection.is_open:
                raise RuntimeError("ESP32 serial connection is unavailable")

            command = f"PAUSE {duration_ms}\n".encode("ascii")
            logger.warning(
                "ESP32 TX command: %r, port=%s",
                command,
                connection.port,
            )

            written = connection.write(command)
            connection.flush()

            logger.warning(
                "ESP32 TX complete: %s bytes",
                written,
            )

    def _set_disconnected(self) -> None:
        with self._lock:
            self._state = RollerReferenceState(
                connected=False,
                triggered=False,
                pulses=self._state.pulses,
                sequence=self._state.sequence,
                generation=self._generation,
            )
            self._last_received = 0.0

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                with serial.Serial(
                    self.port,
                    self.baudrate,
                    timeout=0.1,
                ) as connection:
                    with self._lock:
                        self._generation += 1
                        self._state = RollerReferenceState(
                            connected=False,
                            triggered=False,
                            pulses=self._state.pulses,
                            sequence=self._state.sequence,
                            generation=self._generation,
                        )
                        self._last_received = 0.0

                    logger.info(
                        "ESP32 connected: %s, generation=%s",
                        self.port,
                        self._generation,
                    )

                    with self._lock:
                        self._connection = connection

                    connection.reset_input_buffer()
                    connection.readline()

                    while not self._stop_event.is_set():
                        now = time.monotonic()

                        if now - self._last_ping_sent >= 0.5:
                            with self._lock:
                                connection.write(b"PING\n")
                                connection.flush()

                            self._last_ping_sent = now

                        raw = connection.readline()

                        # Проверяем таймаут ДО обработки нового пакета.
                        # Даже если связь уже восстановилась, сбой фиксируется.
                        with self._lock:
                            state = self._state

                            if (
                                state.connected
                                and time.monotonic() - self._last_received
                                > self.timeout
                            ):
                                self._generation += 1

                                logger.warning(
                                    "ESP32 serial timeout, generation=%s",
                                    self._generation,
                                )

                                self._state = RollerReferenceState(
                                    connected=False,
                                    triggered=False,
                                    pulses=state.pulses,
                                    sequence=state.sequence,
                                    generation=self._generation,
                                )
                                self._last_received = 0.0

                        if not raw:
                            with self._lock:
                                state = self._state

                                if (
                                    state.connected
                                    and time.monotonic() - self._last_received
                                    > self.timeout
                                ):
                                    self._generation += 1

                                    logger.warning(
                                        "ESP32 serial timeout, generation=%s",
                                        self._generation,
                                    )

                                    self._state = RollerReferenceState(
                                        connected=False,
                                        triggered=False,
                                        pulses=state.pulses,
                                        sequence=state.sequence,
                                        generation=self._generation,
                                    )
                                    self._last_received = 0.0

                            continue

                        try:
                            message = json.loads(raw)

                            if message.get("type") != "roller_reference":
                                continue

                            triggered = message["triggered"]
                            pulses = message["pulses"]
                            sequence = message["sequence"]
                            boot_id = message["boot_id"]

                            if (
                                type(triggered) is not bool
                                or type(pulses) is not int
                                or type(sequence) is not int
                                or type(boot_id) is not int
                                or pulses < 0
                                or sequence < 0
                                or not (0 <= boot_id <= 0xFFFFFFFF)
                            ):
                                continue

                            with self._lock:
                                if self._last_received > 0:
                                    gap = time.monotonic() - self._last_received
                                    if gap > 0.3:
                                        logger.warning(
                                            "ESP32 packet gap: %.3f seconds",
                                            gap,
                                        )

                                previous = self._state

                                reboot_detected = (
                                    self._boot_id is not None
                                    and boot_id != self._boot_id
                                )

                                if reboot_detected:
                                    logger.warning(
                                        "ESP32 reboot detected: %s -> %s",
                                        self._boot_id,
                                        boot_id,
                                    )
                                    self._generation += 1

                                self._boot_id = boot_id

                                if (
                                    previous.connected
                                    and not reboot_detected
                                    and sequence <= previous.sequence
                                ):
                                    logger.warning("ESP32 sequence reset or repeated")
                                    self._state = RollerReferenceState(
                                        connected=False,
                                        triggered=False,
                                        pulses=pulses,
                                        sequence=sequence,
                                        generation=self._generation,
                                    )
                                    self._last_received = 0.0
                                    break

                                self._state = RollerReferenceState(
                                    connected=True,
                                    triggered=triggered,
                                    pulses=pulses,
                                    sequence=sequence,
                                    generation=self._generation,
                                )
                                self._last_received = time.monotonic()

                                io_fields = (
                                    "water_switch",
                                    "light_switch",
                                    "water_output",
                                    "light_output",
                                    "watchdog_alive",
                                )

                                counter_fields = (
                                    "water_switch_changes",
                                    "light_switch_changes",
                                )

                                if all(
                                    type(message.get(key)) is bool for key in io_fields
                                ) and all(
                                    type(message.get(key)) is int and message[key] >= 0
                                    for key in counter_fields
                                ):
                                    for key in io_fields + counter_fields:
                                        self._io_state[key] = message[key]
                                self._state_changed.notify_all()

                        except (
                            ValueError,
                            TypeError,
                            KeyError,
                            UnicodeDecodeError,
                        ):
                            logger.warning("Invalid ESP32 serial message")

            except (serial.SerialException, OSError) as exc:
                logger.warning(
                    "ESP32 serial unavailable: %s",
                    exc,
                )

            with self._lock:
                self._connection = None

            self._set_disconnected()
            self._stop_event.wait(1.0)
