from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import Mock

import pytest

from app.services.machine.machine import Machine
from app.services.machine.roller import Roller


def make_machine():
    drive = Mock()
    brush = Mock()
    brush.left_drive = Mock()
    brush.right_drive = Mock()
    return Machine(brush=brush, roller=Roller(drive=drive)), drive


@pytest.mark.parametrize('stop_method', ['stop_roller', 'stop_roller_coast', 'stop_all'])
def test_new_motion_rejected_until_external_stop_callback_finishes(stop_method):
    machine, drive = make_machine()
    entered, proceed = Event(), Event()

    def callback():
        entered.set()
        assert proceed.wait(3)

    if stop_method == 'stop_roller':
        machine.acquire_roller('homing')
    machine.set_roller_external_stop_callback(callback)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(getattr(machine, stop_method))
        try:
            assert entered.wait(3)
            with pytest.raises(RuntimeError, match='pending'):
                machine.start_roller_forward(10)
            with pytest.raises(RuntimeError, match='pending'):
                machine.acquire_roller('homing')
            drive.run_forward.assert_not_called()
        finally:
            proceed.set()
        future.result(timeout=3)

    if stop_method == 'stop_roller':
        machine.release_roller('homing')
    machine.start_roller_forward(10)
    drive.run_forward.assert_called_once()


def test_failed_external_stop_callback_latches_fault():
    machine, drive = make_machine()
    machine.acquire_roller('homing')
    machine.set_roller_external_stop_callback(Mock(side_effect=RuntimeError('callback failed')))
    with pytest.raises(RuntimeError, match='callback failed'):
        machine.stop_roller()
    with pytest.raises(RuntimeError, match='fault is latched'):
        machine.start_roller_forward(10)
    drive.run_forward.assert_not_called()


def test_failed_vfd_stop_latches_fault_and_blocks_motion():
    machine, drive = make_machine()
    drive.stop.side_effect = RuntimeError('VFD timeout')
    with pytest.raises(RuntimeError, match='VFD timeout'):
        machine.stop_roller()
    with pytest.raises(RuntimeError, match='fault is latched'):
        machine.start_roller_reverse(10)
    drive.run_reverse.assert_not_called()
