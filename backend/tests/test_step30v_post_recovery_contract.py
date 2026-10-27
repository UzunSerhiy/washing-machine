"""30V: post-recovery contract with mocked GAIN, no motor commands or hardware."""

import pytest

from tests.test_motion_fault_http_recovery import rig, request, assert_no_commands


def test_ack_does_not_reactivate_auto_or_home(rig):
    status, payload = request(rig)
    assert status == 200, payload
    assert payload['homed'] is False
    assert payload['automatic_restart'] is False
    assert rig.auto.get_status.return_value['running'] is False
    assert rig.auto.get_status.return_value['paused'] is False
    assert rig.home.get_status.return_value['searching'] is False
    assert rig.home.get_status.return_value['awaiting_stop'] is False
    assert_no_commands(rig)


def test_ack_calls_each_session_cleanup_once_before_global_clear(rig):
    events = []
    rig.home.complete_motion_fault_recovery.side_effect = lambda: events.append('HOME')
    rig.auto.complete_motion_fault_recovery.side_effect = lambda: events.append('AUTO')
    rig.calibration.complete_motion_fault_recovery.side_effect = lambda: events.append('CALIBRATION')
    original_clear = rig.machine.complete_motion_fault_recovery

    def clear():
        events.append('GLOBAL')
        original_clear()

    rig.machine.complete_motion_fault_recovery = clear
    assert request(rig)[0] == 200
    assert events == ['HOME', 'AUTO', 'CALIBRATION', 'GLOBAL']
    assert_no_commands(rig)


@pytest.mark.parametrize('service', ('home', 'auto', 'calibration'))
def test_failed_session_cleanup_preserves_global_latch(rig, service):
    getattr(rig, service).complete_motion_fault_recovery.side_effect = RuntimeError('cleanup rejected')
    status, response = request(rig)
    assert status == 409, response
    assert rig.machine.motion_fault_latched == 'E15'
    assert rig.machine.clears == 0
    assert rig.runtime._notified is True
    assert_no_commands(rig)


def test_second_fault_after_success_blocks_recovery_until_fault_cleared(rig):
    assert request(rig)[0] == 200
    rig.machine.motion_fault_latched = 'E15: second event'
    rig.runtime._notified = True
    rig.drives[3].get_fault.return_value = 15
    status, response = request(rig)
    assert status == 409, response
    assert rig.machine.motion_fault_latched == 'E15: second event'
    assert rig.machine.clears == 1
    assert_no_commands(rig)


def test_second_fault_requires_fresh_operator_acknowledgement(rig):
    assert request(rig)[0] == 200
    rig.machine.motion_fault_latched = 'E15: second event'
    rig.runtime._notified = True
    status, response = request(rig, confirmed=False)
    assert status == 409, response
    assert rig.machine.motion_fault_latched == 'E15: second event'
    assert rig.machine.clears == 1
    assert_no_commands(rig)
