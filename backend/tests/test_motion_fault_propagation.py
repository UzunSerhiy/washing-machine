import asyncio
from unittest.mock import Mock

from app.services.machine.motion_fault_runtime import MotionFaultRuntime
from app.services.machine.auto.session_service import AutoSessionService
from app.services.machine.calibration.session_service import CalibrationSessionService
from app.services.machine.roller_homing_service import RollerHomingService


def test_runtime_notifies_once_after_latched_fault():
    async def scenario():
        machine = Mock()
        machine.poll_motion_faults.return_value = "VFD fault 15"
        notified = []
        runtime = MotionFaultRuntime(machine, 0.005, on_fault=notified.append)
        await runtime.start()
        await asyncio.sleep(0.04)
        await runtime.stop()
        assert notified == ["VFD fault 15"]
        assert machine.poll_motion_faults.call_count > 1
    asyncio.run(scenario())


def test_runtime_notification_exception_does_not_restart_notification():
    async def scenario():
        machine = Mock()
        machine.poll_motion_faults.return_value = "offline"
        handler = Mock(side_effect=RuntimeError("handler failed"))
        runtime = MotionFaultRuntime(machine, 0.005, on_fault=handler)
        await runtime.start()
        await asyncio.sleep(0.04)
        await runtime.stop()
        handler.assert_called_once_with("offline")
        assert runtime.last_fault == "offline"
    asyncio.run(scenario())


def test_auto_fault_does_not_issue_second_stop():
    service = AutoSessionService.__new__(AutoSessionService)
    state = Mock(running=True, paused=True)
    service.operation_service = Mock(state=state)
    service._position_loop = None
    service._faulted = False
    service.external_motion_fault("E15")
    assert service._faulted
    assert not state.running and not state.paused
    service.operation_service.machine.stop_all.assert_not_called()


def test_calibration_fault_aborts_without_second_stop():
    service = CalibrationSessionService.__new__(CalibrationSessionService)
    player = Mock()
    service._session = Mock(player=player)
    service._auto_unwinding = True
    service._auto_winding = False
    service._auto_paused = False
    service._saved = True
    service._last_update_time = 10
    service.external_motion_fault("E15")
    assert service._session is None
    assert service._motion_fault == "E15"
    player.external_motion_fault.assert_called_once()
    player.stop.assert_not_called()
    assert not service._auto_unwinding


def test_home_fault_invalidates_zero_without_stop():
    service = RollerHomingService.__new__(RollerHomingService)
    from threading import RLock
    service._state_lock = RLock()
    service._homed = True
    service._awaiting_stop = False
    service._faulted = False
    service._stop_deadline = 5
    service._last_update_time = 5
    service._frequency_hz = 10
    service.homing = Mock()
    service.homing.state = None
    service.machine = Mock()
    # Homing searching property derives from homing state.
    service.external_motion_fault("E15")
    assert not service._homed and service._faulted
    assert service._fault_code == "VFD_MONITOR_FAULT"
    service.machine.stop_roller.assert_not_called()
