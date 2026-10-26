from unittest.mock import Mock
import pytest
from app.services.machine.roller_homing_service import RollerHomingService
from app.services.machine.calibration.stop_confirmation import StopObservation


def setup(fault=0, stopped=True):
    machine = Mock(roller_owner="homing")
    sensor = Mock()
    sensor.get_state.return_value = Mock(connected=True, triggered=False, pulses=0, sequence=1, generation=1)
    obs = Mock(return_value=StopObservation(3, 0.0, 0, stopped))
    f = Mock(return_value=fault)
    service = RollerHomingService(machine, sensor, Mock(), stop_observer=obs, fault_observer=f)
    service._faulted = True
    service._error = "Roller VFD fault 15 during HOME"
    service._fault_code = "VFD_FAULT"
    service.homing._fail(service._error)
    return service, machine, f, obs


def test_acknowledge_requires_operator_confirmation():
    s, m, _, _ = setup()
    with pytest.raises(RuntimeError, match="Operator must confirm"):
        s.acknowledge_fault(operator_confirmed_stopped=False)
    assert s.faulted
    m.release_roller.assert_not_called()


@pytest.mark.parametrize("fault", [15, 1, None, True])
def test_acknowledge_rejects_active_or_invalid_fault(fault):
    s, m, _, _ = setup(fault=fault)
    with pytest.raises(RuntimeError, match="VFD fault"):
        s.acknowledge_fault(operator_confirmed_stopped=True)
    assert s.faulted
    m.release_roller.assert_not_called()


def test_acknowledge_rejects_unconfirmed_stop():
    s, m, _, _ = setup(stopped=False)
    with pytest.raises(RuntimeError, match="stop is not confirmed"):
        s.acknowledge_fault(operator_confirmed_stopped=True)
    assert s.faulted
    m.release_roller.assert_not_called()


def test_acknowledge_requires_three_good_reads_and_does_not_move():
    s, m, f, obs = setup()
    s.acknowledge_fault(operator_confirmed_stopped=True)
    assert not s.faulted
    assert not s.homed
    assert s.get_status()["state"] == "idle"
    assert f.call_count == 3
    assert obs.call_count == 3
    m.release_roller.assert_called_once_with("homing")
    m.start_roller_reverse.assert_not_called()
    m.stop_roller.assert_not_called()


def test_acknowledge_rejects_wrong_owner():
    s, m, _, _ = setup()
    m.roller_owner = "manual"
    with pytest.raises(RuntimeError, match="does not own"):
        s.acknowledge_fault(operator_confirmed_stopped=True)
    assert s.faulted


def test_acknowledge_rejects_missing_telemetry():
    s, _, _, _ = setup()
    s._stop_observer = None
    with pytest.raises(RuntimeError, match="not configured"):
        s.acknowledge_fault(operator_confirmed_stopped=True)
    assert s.faulted


def test_acknowledge_rejects_intermittent_fault():
    s, _, f, _ = setup()
    f.side_effect = [0, 15]
    with pytest.raises(RuntimeError, match="VFD fault"):
        s.acknowledge_fault(operator_confirmed_stopped=True)
    assert s.faulted


def test_acknowledge_rejects_telemetry_exception():
    s, _, f, _ = setup()
    f.side_effect = TimeoutError("modbus")
    with pytest.raises(RuntimeError, match="telemetry unavailable"):
        s.acknowledge_fault(operator_confirmed_stopped=True)
    assert s.faulted
