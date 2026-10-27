"""30ZH.6: real session-service lifecycle with mocked drives; no physical I/O."""
import asyncio
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.services.machine.machine import Machine
from app.services.machine.auto.session_service import AutoSessionService
from app.services.machine.calibration.session_service import CalibrationSessionService
from app.services.machine.roller_homing_service import RollerHomingService
from app.services.machine.motion_fault_recovery import MotionFaultRecoveryService
from app.services.machine.motion_fault_runtime import MotionFaultRuntime


def setup_services():
    brush, roller = Mock(), Mock()
    machine = Machine(brush, roller)
    state = SimpleNamespace(running=False, paused=False)
    operation = SimpleNamespace(state=state, machine=machine)
    auto = AutoSessionService.__new__(AutoSessionService)
    auto.operation_service = operation
    auto._prepared = None
    auto._position_loop = None
    auto._faulted = False
    auto._session_generation = None
    calibration = CalibrationSessionService(machine, Mock())
    home = RollerHomingService(machine, Mock(), Mock())
    drives = {i: Mock() for i in (1, 2, 3)}
    for drive in drives.values():
        drive.get_fault.return_value = 0
        drive.get_status.return_value = 3
        drive.get_frequency.return_value = 0.0
    drive_service = SimpleNamespace(drives=drives, configs={i: SimpleNamespace(enabled=True) for i in drives})
    recovery = MotionFaultRecoveryService(machine, drive_service, auto, calibration, home)
    runtime = MotionFaultRuntime(machine, on_fault=lambda reason: (
        auto.external_motion_fault(reason),
        calibration.external_motion_fault(reason),
        home.external_motion_fault(reason),
    ))
    return machine, brush, roller, auto, calibration, home, recovery, runtime


def inject_fault(machine, runtime):
    with machine._roller_lock:
        machine._motion_fault_latched = 'E15'
        machine._motion_generation += 1
    runtime.on_fault('E15')


def acknowledge(runtime, recovery):
    asyncio.run(runtime.acknowledge_exclusive(recovery, operator_confirmed_stopped=True))


def assert_no_motion(brush, roller):
    brush.start.assert_not_called()
    roller.forward.assert_not_called()
    roller.reverse.assert_not_called()


def test_real_services_fault_then_recovery_clear_state_without_motion():
    machine, brush, roller, auto, calibration, home, recovery, runtime = setup_services()
    token = machine.capture_session_generation()
    auto._position_loop = SimpleNamespace(position=Mock())
    calibration._session = SimpleNamespace(player=Mock())
    calibration._session_generation = token
    home._homed = True
    inject_fault(machine, runtime)
    assert auto.get_status()['status'] == 'FAULT'
    assert not calibration.active
    assert not home.homed
    acknowledge(runtime, recovery)
    assert machine.motion_fault_latched is None
    assert auto.get_status()['status'] == 'IDLE'
    assert not calibration.active
    assert not home.homed
    with pytest.raises(RuntimeError, match='Stale motion session'):
        machine.start_roller_forward(10, session_generation=token)
    assert_no_motion(brush, roller)


def test_real_services_recovery_refuses_running_auto_and_keeps_latch():
    machine, brush, roller, auto, calibration, home, recovery, runtime = setup_services()
    inject_fault(machine, runtime)
    auto.operation_service.state.running = True
    with pytest.raises(RuntimeError, match='AUTO session is not inactive'):
        acknowledge(runtime, recovery)
    assert machine.motion_fault_latched == 'E15'
    assert_no_motion(brush, roller)


def test_real_services_recovery_cleanup_error_preserves_latch():
    machine, brush, roller, auto, calibration, home, recovery, runtime = setup_services()
    inject_fault(machine, runtime)
    calibration._session = SimpleNamespace(player=Mock())
    with pytest.raises(RuntimeError, match='CALIBRATION session is active'):
        acknowledge(runtime, recovery)
    assert machine.motion_fault_latched == 'E15'
    assert_no_motion(brush, roller)
