import pytest

from app.services.machine.repository import MachineRepository


class FakeResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class FakeSession:
    def __init__(self, value):
        self.value = value
        self.execute_calls = 0

    async def execute(self, statement):
        self.execute_calls += 1
        return FakeResult(self.value)


class FakeMachine:
    def __init__(self, machine_id: int):
        self.id = machine_id
        self.roller_core_diameter_mm = 200.0


@pytest.mark.anyio
async def test_load_returns_machine():
    machine = FakeMachine(machine_id=1)
    session = FakeSession(machine)

    repository = MachineRepository()

    result = await repository.load(
        session=session,
        machine_id=1,
    )

    assert result is machine
    assert session.execute_calls == 1


@pytest.mark.anyio
async def test_load_raises_when_machine_not_found():
    session = FakeSession(None)

    repository = MachineRepository()

    with pytest.raises(
        RuntimeError,
        match="Machine not found",
    ):
        await repository.load(
            session=session,
            machine_id=1,
        )
