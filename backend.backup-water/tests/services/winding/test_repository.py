import pytest

from app.services.winding.repository import WindingParametersRepository


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


class FakeParameters:
    def __init__(self, material_profile_id: int):
        self.material_profile_id = material_profile_id


@pytest.mark.anyio
async def test_load_returns_winding_parameters():
    parameters = FakeParameters(material_profile_id=7)
    session = FakeSession(parameters)

    repository = WindingParametersRepository()

    result = await repository.load(
        session=session,
        material_profile_id=7,
    )

    assert result is parameters
    assert session.execute_calls == 1


@pytest.mark.anyio
async def test_load_raises_when_parameters_not_found():
    session = FakeSession(None)

    repository = WindingParametersRepository()

    with pytest.raises(
        RuntimeError,
        match="Winding parameters not found",
    ):
        await repository.load(
            session=session,
            material_profile_id=7,
        )
