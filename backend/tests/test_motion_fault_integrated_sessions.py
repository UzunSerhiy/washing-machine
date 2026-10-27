"""29E.3: real session handlers through runtime, with mocked drives only."""
import asyncio
from threading import RLock
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.services.machine.machine import Machine
from app.services.machine.motion_fault_runtime import MotionFaultRuntime
from app.services.machine.motion_fault_store import MotionFaultStore
from app.services.machine.auto.session_service import AutoSessionService
from app.services.machine.calibration.session_service import CalibrationSessionService
from app.services.machine.calibration.homing import HomingState
from app.services.machine.roller_homing_service import RollerHomingService


def scenario(tmp_path):
    store = MotionFaultStore(tmp_path / 'fault.json')
    store.write_latch(None)
    drives = [Mock() for _ in range(3)]
    for drive in drives:
        drive.get_fault.return_value = 0
    brush = Mock(left_drive=drives[0], right_drive=drives[1])
    roller = Mock(drive=drives[2])
    machine = Machine(brush, roller, enforce_motion_preflight=True, motion_fault_store=store)

    auto = AutoSessionService.__new__(AutoSessionService)
    auto.operation_service = SimpleNamespace(state=SimpleNamespace(running=True, paused=False), machine=machine)
    position = Mock()
    auto._position_loop = SimpleNamespace(position=position)
    auto._faulted = False
    auto._prepared = object()

    calibration = CalibrationSessionService.__new__(CalibrationSessionService)
    player = Mock()
    calibration._session = SimpleNamespace(player=player)
    calibration._motion_fault = None
    calibration._auto_unwinding = True
    calibration._auto_winding = False
    calibration._auto_paused = False
    calibration._saved = True
    calibration._last_update_time = 1
    calibration.machine = machine

    home = RollerHomingService.__new__(RollerHomingService)
    home._state_lock = RLock()
    home.homing = Mock(state=HomingState.SEARCHING)
    home._homed = True
    home._awaiting_stop = True
    home._stop_deadline = 10
    home._faulted = False
    home._last_update_time = 1
    home._frequency_hz = 10
    home.machine = machine

    def notify(reason):
        for service in (auto, calibration, home):
            try:
                service.external_motion_fault(reason)
            except Exception:
                pass

    return machine, brush, roller, drives, store, auto, calibration, home, position, player, MotionFaultRuntime(machine, on_fault=notify)


def test_dispatch_fault_aborts_all_real_sessions(tmp_path):
    machine, brush, roller, drives, store, auto, cal, home, position, player, runtime = scenario(tmp_path)
    roller.forward.side_effect = RuntimeError('GAIN E15 during RUN')
    with pytest.raises(RuntimeError, match='E15'):
        machine.start_roller_forward(10)
    asyncio.run(runtime._poll_once())
    assert store.read_latch() == machine.motion_fault_latched
    assert auto._faulted and not auto.operation_service.state.running
    position.invalidate.assert_called_once_with()
    assert not cal.active and cal.saved is False
    player.external_motion_fault.assert_called_once_with()
    assert home.faulted and not home.homed
    home.homing._fail.assert_called_once()
    with pytest.raises(RuntimeError, match='latched'):
        machine.start_roller_reverse(10)
    roller.reverse.assert_not_called()


def test_broken_auto_handler_does_not_prevent_other_real_handlers(tmp_path):
    machine, brush, roller, drives, store, auto, cal, home, position, player, runtime = scenario(tmp_path)
    position.invalidate.side_effect = RuntimeError('position failure')
    drives[0].get_fault.return_value = 15
    asyncio.run(runtime._poll_once())
    assert machine.motion_fault_latched and store.read_latch()
    assert not cal.active and cal._motion_fault is not None
    assert home.faulted and not home.homed
    assert runtime._notified
    asyncio.run(runtime._poll_once())
    assert home.homing._fail.call_count == 1


def test_recovery_refuses_prepared_auto_and_does_not_restart(tmp_path):
    machine, brush, roller, drives, store, auto, cal, home, position, player, runtime = scenario(tmp_path)
    roller.forward.side_effect = OSError('RS485 timeout')
    with pytest.raises(OSError, match='timeout'):
        machine.start_roller_forward(10)
    asyncio.run(runtime._poll_once())
    with pytest.raises(RuntimeError, match='AUTO still active'):
        auto.complete_motion_fault_recovery()
    assert machine.motion_fault_latched
    assert store.read_latch()
    assert not auto.operation_service.state.running
    brush.start.assert_not_called()
    roller.reverse.assert_not_called()
