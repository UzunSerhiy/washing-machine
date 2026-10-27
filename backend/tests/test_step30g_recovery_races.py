"""30G: deterministic concurrent recovery/command tests; simulated GAIN only."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.services.machine.brush import Brush
from app.services.machine.machine import Machine
from app.services.machine.roller import Roller
from app.services.machine.motion_fault_recovery import MotionFaultRecoveryService


def build():
    left, right, roller = (Mock() for _ in range(3))
    for drive in (left, right, roller):
        drive.get_fault.return_value = 0
        drive.get_status.return_value = 3
        drive.get_frequency.return_value = 0.0
    machine = Machine(Brush(left, right), Roller(roller), enforce_motion_preflight=True)
    machine._motion_fault_latched = 'E15'
    auto = Mock()
    auto.get_status.return_value = {'status': 'FAULT', 'running': False, 'paused': False}
    auto._prepared = None
    calibration = Mock(active=False, auto_mode=None)
    home = Mock(OWNER='homing')
    home.get_status.return_value = {'state': 'FAULT', 'searching': False, 'awaiting_stop': False}
    service = MotionFaultRecoveryService(
        machine,
        SimpleNamespace(drives={1: left, 2: right, 3: roller},
                        configs={i: SimpleNamespace(enabled=True) for i in (1, 2, 3)}),
        auto, calibration, home,
    )
    return SimpleNamespace(machine=machine, service=service, left=left, right=right,
                           roller=roller, auto=auto, home=home, calibration=calibration)


def assert_no_run(rig):
    for drive in (rig.left, rig.right, rig.roller):
        drive.run_forward.assert_not_called()
        drive.run_reverse.assert_not_called()
        drive.set_frequency.assert_not_called()


@pytest.mark.parametrize('method', ('start_brush', 'start_roller_forward', 'start_roller_reverse'))
def test_run_during_failed_recovery_never_dispatches(method):
    rig = build()
    entered, release = Event(), Event()

    def blocked_telemetry():
        entered.set()
        assert release.wait(3), 'telemetry gate timed out'
        return 0

    rig.left.get_fault.side_effect = blocked_telemetry
    rig.right.get_fault.return_value = 15  # Recovery must fail after gate opens.
    with ThreadPoolExecutor(max_workers=2) as pool:
        recovery = pool.submit(rig.service.acknowledge, operator_confirmed_stopped=True)
        assert entered.wait(3)
        motion = pool.submit(getattr(rig.machine, method), 10)
        try:
            assert not motion.done(), 'RUN bypassed machine lock during recovery'
        finally:
            release.set()
        with pytest.raises(RuntimeError, match='fault not cleared'):
            recovery.result(timeout=3)
        with pytest.raises(RuntimeError, match='Motion fault latched'):
            motion.result(timeout=3)
    assert rig.machine.motion_fault_latched == 'E15'
    assert_no_run(rig)


def test_recovery_cleanup_holds_lock_against_queued_run():
    rig = build()
    entered, release = Event(), Event()

    def cleanup():
        entered.set()
        assert release.wait(3), 'cleanup gate timed out'
        raise RuntimeError('HOME cleanup rejected')

    rig.home.complete_motion_fault_recovery.side_effect = cleanup
    with ThreadPoolExecutor(max_workers=2) as pool:
        recovery = pool.submit(rig.service.acknowledge, operator_confirmed_stopped=True)
        assert entered.wait(3)
        motion = pool.submit(rig.machine.start_roller_forward, 10)
        try:
            assert not motion.done(), 'RUN bypassed recovery cleanup lock'
        finally:
            release.set()
        with pytest.raises(RuntimeError, match='HOME cleanup rejected'):
            recovery.result(timeout=3)
        with pytest.raises(RuntimeError, match='Motion fault latched'):
            motion.result(timeout=3)
    assert rig.machine.motion_fault_latched == 'E15'
    assert_no_run(rig)


def test_recovery_rejects_prepared_auto_and_never_dispatches():
    rig = build()
    rig.auto._prepared = object()
    with pytest.raises(RuntimeError, match='AUTO prepared'):
        rig.service.acknowledge(operator_confirmed_stopped=True)
    assert rig.machine.motion_fault_latched == 'E15'
    assert_no_run(rig)


def test_recovery_rejects_owned_roller_and_never_dispatches():
    rig = build()
    rig.machine._roller_owner = 'auto'
    with pytest.raises(RuntimeError, match='Roller owned'):
        rig.service.acknowledge(operator_confirmed_stopped=True)
    assert rig.machine.motion_fault_latched == 'E15'
    assert_no_run(rig)
