from concurrent.futures import ThreadPoolExecutor
from threading import Event, Thread
from unittest.mock import Mock

from app.services.machine.roller_homing_service import RollerHomingService


def make_service():
    machine = Mock()
    machine.roller_owner = None

    def acquire(owner):
        if machine.roller_owner is not None:
            raise RuntimeError('already reserved')
        machine.roller_owner = owner

    def release(owner):
        if machine.roller_owner != owner:
            raise RuntimeError('owner mismatch')
        machine.roller_owner = None

    machine.acquire_roller.side_effect = acquire
    machine.release_roller.side_effect = release
    sensor = Mock()
    sensor.get_state.return_value = Mock(connected=True, triggered=False, pulses=0, sequence=1, generation=1)
    calculator = Mock()
    calculator.revolutions_for_time.return_value = 0.01
    return RollerHomingService(machine, sensor, calculator), machine


def test_cancel_waits_for_inflight_start_and_stops_it():
    service, machine = make_service()
    entered, proceed = Event(), Event()

    def slow_start(*args, **kwargs):
        entered.set()
        assert proceed.wait(2)

    machine.start_roller_reverse.side_effect = slow_start
    starter = Thread(target=lambda: service.start(position_confirmed=True))
    starter.start()
    assert entered.wait(2)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(service.cancel)
        proceed.set()
        future.result(timeout=2)
    starter.join(timeout=2)
    assert not starter.is_alive()
    assert not service.searching
    assert machine.roller_owner is None
    machine.stop_roller.assert_called_once_with(owner='homing')


def test_concurrent_starts_only_issue_one_reverse_command():
    service, machine = make_service()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: try_start(service), range(2)))
    assert results.count('started') == 1
    assert results.count('rejected') == 1
    machine.start_roller_reverse.assert_called_once()
    service.cancel()


def try_start(service):
    try:
        service.start(position_confirmed=True)
        return 'started'
    except RuntimeError:
        return 'rejected'


def test_external_stop_waits_for_inflight_start():
    service, machine = make_service()
    entered, proceed = Event(), Event()

    def slow_start(*args, **kwargs):
        entered.set()
        assert proceed.wait(2)

    machine.start_roller_reverse.side_effect = slow_start
    starter = Thread(target=lambda: service.start(position_confirmed=True))
    starter.start()
    assert entered.wait(2)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(service.external_stop)
        proceed.set()
        future.result(timeout=2)
    starter.join(timeout=2)
    assert not starter.is_alive()
    assert not service.searching
    assert machine.roller_owner is None
