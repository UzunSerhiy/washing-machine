import asyncio
from types import SimpleNamespace
from unittest.mock import Mock
import pytest

from app.services.machine.motion_fault_recovery import MotionFaultRecoveryService
from app.services.machine.motion_fault_runtime import MotionFaultRuntime


def build():
    drives = {i: Mock() for i in (1, 2, 3)}
    for drive in drives.values():
        drive.get_fault.return_value = 0
        drive.get_status.return_value = 3
        drive.get_frequency.return_value = 0.0
    from threading import RLock
    class Machine:
        _roller_lock = RLock()
        motion_fault_latched = 'E15'
        _roller_stop_fault = False
        _external_stop_pending = 0
        roller_owner = None
        def complete_motion_fault_recovery(self):
            self.motion_fault_latched = None
    machine = Machine()
    auto = Mock()
    auto.get_status.return_value = {'status': 'FAULT', 'running': False, 'paused': False}
    auto._prepared = None
    calibration = Mock()
    calibration.active = False
    calibration.auto_mode = None
    home = Mock()
    home.get_status.return_value = {'state': 'FAULT', 'searching': False, 'awaiting_stop': False}
    home.OWNER = 'homing'
    recovery = MotionFaultRecoveryService(machine,
        SimpleNamespace(drives=drives, configs={i: SimpleNamespace(enabled=True) for i in drives}),
        auto, calibration, home)
    return machine, recovery, drives, auto, calibration, home


def test_acknowledge_clears_machine_last_without_drive_commands():
    machine, recovery, drives, auto, calibration, home = build()
    result = recovery.acknowledge(operator_confirmed_stopped=True)
    assert result.verified
    assert machine.motion_fault_latched is None
    home.complete_motion_fault_recovery.assert_called_once()
    auto.complete_motion_fault_recovery.assert_called_once()
    calibration.complete_motion_fault_recovery.assert_called_once()
    for drive in drives.values():
        drive.run_forward.assert_not_called()
        drive.run_reverse.assert_not_called()
        drive.stop.assert_not_called()


def test_failed_telemetry_preserves_latches():
    machine, recovery, drives, auto, calibration, home = build()
    drives[2].get_fault.return_value = 15
    with pytest.raises(RuntimeError):
        recovery.acknowledge(operator_confirmed_stopped=True)
    assert machine.motion_fault_latched == 'E15'
    home.complete_motion_fault_recovery.assert_not_called()


def test_failed_home_cleanup_preserves_machine_latch():
    machine, recovery, _, auto, calibration, home = build()
    home.complete_motion_fault_recovery.side_effect = RuntimeError('owner mismatch')
    with pytest.raises(RuntimeError):
        recovery.acknowledge(operator_confirmed_stopped=True)
    assert machine.motion_fault_latched == 'E15'
    auto.complete_motion_fault_recovery.assert_not_called()


def test_monitor_notification_rearmed_only_after_success():
    machine, recovery, drives, _, _, _ = build()
    runtime = MotionFaultRuntime(Mock())
    runtime._notified = True
    runtime.last_fault = 'E15'
    drives[1].get_fault.return_value = 15
    with pytest.raises(RuntimeError):
        asyncio.run(runtime.acknowledge_exclusive(recovery, operator_confirmed_stopped=True))
    assert runtime._notified
    drives[1].get_fault.return_value = 0
    asyncio.run(runtime.acknowledge_exclusive(recovery, operator_confirmed_stopped=True))
    assert not runtime._notified
    assert runtime.last_fault is None
