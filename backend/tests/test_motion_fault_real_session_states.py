"""29E.2: actual session class fault handlers; mocked hardware, no I/O."""
from threading import RLock
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.services.machine.auto.session_service import AutoSessionService
from app.services.machine.calibration.session_service import CalibrationSessionService
from app.services.machine.calibration.homing import HomingState
from app.services.machine.roller_homing_service import RollerHomingService


def test_auto_fault_disables_session_and_invalidates_position_without_io():
    service = AutoSessionService.__new__(AutoSessionService)
    state = SimpleNamespace(running=True, paused=True)
    machine = Mock()
    service.operation_service = SimpleNamespace(state=state, machine=machine)
    position = Mock()
    service._position_loop = SimpleNamespace(position=position)
    service._faulted = False
    service._prepared = object()

    service.external_motion_fault('E15')
    assert service._faulted is True
    assert not state.running and not state.paused
    assert service.position_loop is None
    position.invalidate.assert_called_once_with()
    machine.stop_all.assert_not_called()
    with pytest.raises(RuntimeError, match='fault state'):
        service.start()
    with pytest.raises(RuntimeError, match='AUTO still active'):
        service.complete_motion_fault_recovery()


def test_calibration_fault_discards_active_session_and_blocks_restart():
    service = CalibrationSessionService.__new__(CalibrationSessionService)
    player = Mock()
    service._session = SimpleNamespace(player=player)
    service._motion_fault = None
    service._auto_unwinding = True
    service._auto_winding = True
    service._auto_paused = True
    service._saved = True
    service._last_update_time = 123
    service.machine = Mock()

    service.external_motion_fault('RS485 timeout')
    assert not service.active
    assert service.auto_mode is None
    assert service.saved is False
    assert service._last_update_time is None
    player.external_motion_fault.assert_called_once_with()
    service.machine.stop_all.assert_not_called()
    with pytest.raises(RuntimeError, match='motion fault latched'):
        service.start(1)
    with pytest.raises(RuntimeError, match='motion fault latched'):
        service.get_current()


def test_home_fault_invalidates_point0_and_keeps_owner_without_io():
    service = RollerHomingService.__new__(RollerHomingService)
    service._state_lock = RLock()
    service.homing = Mock(state=HomingState.SEARCHING)
    service._homed = True
    service._awaiting_stop = True
    service._stop_deadline = 123
    service._faulted = False
    service._last_update_time = 123
    service._frequency_hz = 10
    service.machine = Mock()

    service.external_motion_fault('GAIN E15')
    assert not service.homed
    assert service.faulted
    assert service._fault_code == 'VFD_MONITOR_FAULT'
    assert not service._awaiting_stop
    assert service._stop_deadline is None
    assert service._last_update_time is None
    assert service._frequency_hz is None
    service.homing._fail.assert_called_once_with('GAIN E15')
    service.machine.release_roller.assert_not_called()
    service.machine.stop_roller.assert_not_called()
    with pytest.raises(RuntimeError, match='Point 0'):
        service.require_zero()


def test_home_idle_fault_still_invalidates_reference_without_second_stop():
    service = RollerHomingService.__new__(RollerHomingService)
    service._state_lock = RLock()
    service.homing = Mock(state=HomingState.COMPLETED)
    service._homed = True
    service._awaiting_stop = False
    service._faulted = False
    service.machine = Mock()

    service.external_motion_fault('Telemetry unavailable')
    assert not service.homed
    assert service.faulted
    service.homing._fail.assert_not_called()
    service.machine.release_roller.assert_not_called()
    service.machine.stop_roller.assert_not_called()
