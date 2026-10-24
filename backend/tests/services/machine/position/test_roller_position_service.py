import pytest

from app.services.machine.position.roller_position_service import RollerPositionService
from app.services.machine.sensors.roller_reference import RollerReferenceState
from app.services.winding.rotation import RollerRotationCalculator


def sensor(pulses=20, *, connected=True, triggered=False, generation=1):
    return RollerReferenceState(connected, triggered, pulses, pulses, generation)


@pytest.fixture
def service():
    obj = RollerPositionService(RollerRotationCalculator(905, 100))
    obj.home(sensor(triggered=True))
    return obj


def test_requires_home():
    obj = RollerPositionService(RollerRotationCalculator(905, 100))
    with pytest.raises(RuntimeError, match="HOME required"):
        obj.advance(elapsed_seconds=1, frequency_hz=50, direction=1, sensor=sensor())


def test_estimates_fractional_turn(service):
    result = service.advance(elapsed_seconds=3, frequency_hz=50, direction=1, sensor=sensor())
    assert result.position_turns == pytest.approx(9.05 * 3 / 60)


def test_pulse_corrects_position(service):
    service.advance(elapsed_seconds=6, frequency_hz=50, direction=1, sensor=sensor())
    result = service.advance(elapsed_seconds=0.6, frequency_hz=50, direction=1, sensor=sensor(21))
    assert result.position_turns == 1
    assert result.pulse_count_since_home == 1


def test_reverse_pulses(service):
    result = service.advance(elapsed_seconds=6.6, frequency_hz=50, direction=-1, sensor=sensor(21))
    assert result.position_turns == -1
    assert result.pulse_count_since_home == -1


def test_stop_does_not_integrate(service):
    result = service.advance(elapsed_seconds=10, frequency_hz=50, direction=0, sensor=sensor())
    assert result.position_turns == 0
    assert result.estimated_rpm == 0


def test_sensor_disconnect_invalidates(service):
    with pytest.raises(RuntimeError, match="HOME required"):
        service.advance(elapsed_seconds=0.1, frequency_hz=50, direction=1, sensor=sensor(connected=False))
    assert not service.snapshot.valid


def test_sensor_reboot_invalidates(service):
    with pytest.raises(RuntimeError, match="HOME required"):
        service.advance(elapsed_seconds=0.1, frequency_hz=50, direction=1, sensor=sensor(generation=2))
    assert not service.snapshot.valid


def test_counter_reset_invalidates(service):
    with pytest.raises(RuntimeError, match="HOME required"):
        service.advance(elapsed_seconds=0.1, frequency_hz=50, direction=1, sensor=sensor(19))
    assert not service.snapshot.valid


def test_pulse_while_stopped_invalidates(service):
    with pytest.raises(RuntimeError, match="position uncertain"):
        service.advance(elapsed_seconds=1, frequency_hz=0, direction=0, sensor=sensor(21))
    assert not service.snapshot.valid


def test_invalid_arguments(service):
    with pytest.raises(ValueError):
        service.advance(elapsed_seconds=-1, frequency_hz=50, direction=1, sensor=sensor())
    with pytest.raises(ValueError):
        service.advance(elapsed_seconds=1, frequency_hz=50, direction=2, sensor=sensor())
