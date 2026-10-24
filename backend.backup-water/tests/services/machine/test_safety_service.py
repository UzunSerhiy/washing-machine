import pytest

from app.services.machine.safety_service import MachineSafetyService


class FakeSafetyProvider:
    def is_safe(self) -> bool:
        return False


class FakeSafeProvider:
    def is_safe(self) -> bool:
        return True


def test_safety_service_rejects_missing_confirmation():
    service = MachineSafetyService()

    with pytest.raises(RuntimeError, match="safety"):
        service.require_safe_state()


def test_safety_service_rejects_unsafe_provider():
    provider = FakeSafetyProvider()

    service = MachineSafetyService(
        safety_provider=provider,
    )

    with pytest.raises(RuntimeError, match="safety"):
        service.require_safe_state()


def test_safety_service_accepts_safe_provider():
    provider = FakeSafeProvider()

    service = MachineSafetyService(
        safety_provider=provider,
    )

    assert service.require_safe_state() is None


class FakeFailingSafetyProvider:
    def is_safe(self) -> bool:
        raise OSError("Safety controller communication lost")


def test_safety_service_rejects_provider_failure():
    provider = FakeFailingSafetyProvider()

    service = MachineSafetyService(
        safety_provider=provider,
    )

    with pytest.raises(
        RuntimeError,
        match="safety",
    ) as exc_info:
        service.require_safe_state()

    assert isinstance(exc_info.value.__cause__, OSError)
    assert str(exc_info.value.__cause__) == "Safety controller communication lost"
