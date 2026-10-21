from app.services.machine.sensors.roller_reference import (
    RollerReferenceState,
)


class FakeRollerReferenceSensor:
    def __init__(self) -> None:
        self._connected = True
        self._triggered = False
        self._pulses = 0
        self._sequence = 0

    def read(self) -> RollerReferenceState:
        return RollerReferenceState(
            connected=self._connected,
            triggered=self._triggered,
            pulses=self._pulses,
            sequence=self._sequence,
        )

    def set_triggered(self, triggered: bool) -> None:
        if triggered and not self._triggered:
            self._pulses += 1

        self._triggered = triggered
        self._sequence += 1

    def set_connected(self, connected: bool) -> None:
        self._connected = connected
        self._sequence += 1

    def reset_pulses(self) -> None:
        self._pulses = 0
        self._sequence += 1
