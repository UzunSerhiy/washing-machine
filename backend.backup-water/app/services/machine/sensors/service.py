from app.services.machine.sensors.roller_reference import (
    RollerReferenceSensor,
    RollerReferenceState,
)


class RollerSensorService:
    def __init__(self, sensor: RollerReferenceSensor) -> None:
        self.sensor = sensor

    def get_state(self) -> RollerReferenceState:
        return self.sensor.read()

    def is_ready(self) -> bool:
        return self.sensor.read().connected

    def is_triggered(self) -> bool:
        state = self.sensor.read()

        if not state.connected:
            raise RuntimeError("Roller reference sensor is disconnected")

        return state.triggered
