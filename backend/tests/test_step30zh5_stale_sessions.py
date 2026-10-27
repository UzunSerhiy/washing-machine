"""30ZH.5: recovery invalidates old motion epochs; no physical drives."""
import asyncio
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.services.machine.machine import Machine
from app.services.machine.motion_fault_recovery import MotionFaultRecoveryService
from app.services.machine.motion_fault_runtime import MotionFaultRuntime


def fixture():
    brush = Mock()
    roller = Mock()
    machine = Machine(brush, roller)
    drives = {i: Mock() for i in (1, 2, 3)}
    for drive in drives.values():
        drive.get_fault.return_value = 0
        drive.get_status.return_value = 3
        drive.get_frequency.return_value = 0.0
    drive_service = SimpleNamespace(
        drives=drives,
        configs={i: SimpleNamespace(enabled=True) for i in drives},
    )
    auto = Mock()
    auto.get_status.return_value = {'status': 'FAULT', 'running': False, 'paused': False}
    auto._prepared = None
    calibration = Mock()
    calibration.active = False
    calibration.auto_mode = None
    home = Mock()
    home.OWNER = 'homing'
    home.get_status.return_value = {'state': 'FAULT', 'searching': False, 'awaiting_stop': False}
    recovery = MotionFaultRecoveryService(machine, drive_service, auto, calibration, home)
    runtime = MotionFaultRuntime(machine, on_fault=lambda _: None)
    return machine, brush, roller, drives, auto, calibration, home, recovery, runtime


def latch(machine):
    # Fake E15 event: software latch and generation update, no VFD commands.
    with machine._roller_lock:
        machine._motion_fault_latched = 'E15'
        machine._motion_generation += 1


def assert_no_run(brush, roller, drives):
    brush.start.assert_not_called()
    roller.forward.assert_not_called()
    roller.reverse.assert_not_called()
    for drive in drives.values():
        drive.run_forward.assert_not_called()
        drive.run_reverse.assert_not_called()
        drive.set_frequency.assert_not_called()


def test_old_auto_home_calibration_epochs_rejected_after_recovery():
    machine, brush, roller, drives, auto, calibration, home, recovery, runtime = fixture()
    tokens = {name: machine.capture_session_generation() for name in ('AUTO', 'HOME', 'CALIBRATION')}
    latch(machine)
    async def scenario():
        await runtime.acknowledge_exclusive(recovery, operator_confirmed_stopped=True)
    asyncio.run(scenario())
    assert machine.motion_fault_latched is None
    for token in tokens.values():
        with pytest.raises(RuntimeError, match='Stale motion session'):
            machine.require_session_generation(token)
        with pytest.raises(RuntimeError, match='Stale motion session'):
            machine.start_brush(10, session_generation=token)
        with pytest.raises(RuntimeError, match='Stale motion session'):
            machine.start_roller_forward(10, session_generation=token)
        with pytest.raises(RuntimeError, match='Stale motion session'):
            machine.start_roller_reverse(10, session_generation=token)
    assert_no_run(brush, roller, drives)
    assert machine.capture_session_generation() != tokens['AUTO']


def test_physical_reset_without_software_ack_does_not_authorize_run():
    machine, brush, roller, drives, auto, calibration, home, recovery, runtime = fixture()
    token = machine.capture_session_generation()
    latch(machine)
    # Fake drives report STOP and no fault, equivalent to physical reset telemetry.
    with pytest.raises(RuntimeError, match='Motion fault latched'):
        machine.start_brush(10, session_generation=token)
    with pytest.raises(RuntimeError, match='Motion fault latched'):
        machine.start_roller_forward(10, session_generation=token)
    assert machine.motion_fault_latched == 'E15'
    assert_no_run(brush, roller, drives)


def test_failed_recovery_keeps_all_old_epochs_blocked():
    machine, brush, roller, drives, auto, calibration, home, recovery, runtime = fixture()
    token = machine.capture_session_generation()
    latch(machine)
    drives[2].get_status.return_value = 1
    async def scenario():
        with pytest.raises(RuntimeError, match='STOP not confirmed'):
            await runtime.acknowledge_exclusive(recovery, operator_confirmed_stopped=True)
    asyncio.run(scenario())
    assert machine.motion_fault_latched == 'E15'
    with pytest.raises(RuntimeError, match='Motion fault latched'):
        machine.start_brush(10, session_generation=token)
    assert_no_run(brush, roller, drives)


def test_recovery_cleanup_failure_keeps_global_latch():
    machine, brush, roller, drives, auto, calibration, home, recovery, runtime = fixture()
    token = machine.capture_session_generation()
    latch(machine)
    calibration.complete_motion_fault_recovery.side_effect = RuntimeError('cleanup failed')
    async def scenario():
        with pytest.raises(RuntimeError, match='cleanup failed'):
            await runtime.acknowledge_exclusive(recovery, operator_confirmed_stopped=True)
    asyncio.run(scenario())
    assert machine.motion_fault_latched == 'E15'
    with pytest.raises(RuntimeError, match='Motion fault latched'):
        machine.start_roller_reverse(10, session_generation=token)
    assert_no_run(brush, roller, drives)
