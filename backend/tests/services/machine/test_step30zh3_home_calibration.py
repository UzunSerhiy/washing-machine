from threading import Event, Thread
from types import SimpleNamespace
import pytest
from app.services.machine.operation_service import MachineOperationService
from app.services.machine.operation import OperationMode


class FakeMachine:
    def stop_all(self):
        pass


def test_home_start_blocks_mode_transition_until_start_returns():
    operation = MachineOperationService(FakeMachine())
    operation.state.mode = OperationMode.MANUAL
    entered, release, switched = Event(), Event(), Event()

    class Home:
        def start(self, **kwargs):
            entered.set()
            assert release.wait(2)
        searching = False

    home = Home()
    operation.set_roller_homing_service(home)
    t1 = Thread(target=lambda: operation.start_home(home, position_confirmed=True, frequency_hz=5))
    t2 = Thread(target=lambda: (operation.set_auto_mode(1), switched.set()))
    t1.start()
    try:
        assert entered.wait(2)
        t2.start()
        assert not switched.wait(0.05)
    finally:
        release.set()
        t1.join(2)
        if t2.ident is not None:
            t2.join(2)
    assert switched.is_set()
    assert operation.state.mode == OperationMode.AUTO


def test_home_rejects_start_outside_manual():
    operation = MachineOperationService(FakeMachine())
    operation.set_auto_mode(1)
    class Home:
        def start(self, **kwargs):
            pytest.fail("HOME started in AUTO")
    with pytest.raises(RuntimeError, match="MANUAL"):
        operation.start_home(Home(), position_confirmed=True, frequency_hz=5)


def test_calibration_rejects_stale_mode_revision():
    from app.services.machine.calibration.session_service import CalibrationSessionService
    operation = MachineOperationService(FakeMachine())
    operation.set_calibration_mode(1)
    service = CalibrationSessionService(machine=FakeMachine(), rotation_calculator=None)
    service.set_operation_service(operation)
    service._session = SimpleNamespace()
    service._session_generation = 0
    service._session_mode_revision = operation._mode_revision
    service._require_session_generation = lambda: None
    assert service.get_current() is service._session
    operation.set_manual_mode()
    operation.set_calibration_mode(1)
    with pytest.raises(RuntimeError, match="previous mode revision"):
        service.get_current()
