from app.services.machine.machine import Machine


class MachineService:
    def __init__(self, machine: Machine):
        self.machine = machine

    def start(self) -> None:
        self.machine.start_brush(10)
        self.machine.start_roller_forward(10)

    def stop(self) -> None:
        self.machine.stop_all()
