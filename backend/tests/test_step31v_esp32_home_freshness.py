"""Step 31V: ESP32 HOME freshness regressions; no serial ports or drives."""
from unittest.mock import Mock

import pytest

from app.services.machine.sensors.serial_reference import SerialRollerReferenceSensor
from app.services.machine.sensors.roller_reference import RollerReferenceState
from app.services.machine.sensors.service import RollerSensorService
from app.services.machine.calibration.homing import HomingService, HomingState


def test_stale_triggered_packet_is_not_reported_as_home(monkeypatch):
    sensor = SerialRollerReferenceSensor(timeout=0.5)
    sensor._state = RollerReferenceState(True, True, 4, 9, 2)
    sensor._generation = 2
    sensor._last_received = 10.0
    monkeypatch.setattr('app.services.machine.sensors.serial_reference.time.monotonic', lambda: 10.6)
    state = sensor.read()
    assert not state.connected
    assert not state.triggered
    assert state.generation == 3
    with pytest.raises(RuntimeError, match='disconnected'):
        RollerSensorService(sensor).is_triggered()


def test_timeout_generation_changes_once(monkeypatch):
    sensor = SerialRollerReferenceSensor(timeout=0.5)
    sensor._state = RollerReferenceState(True, False, 0, 1, 4)
    sensor._generation = 4
    sensor._last_received = 10.0
    monkeypatch.setattr('app.services.machine.sensors.serial_reference.time.monotonic', lambda: 11.0)
    assert sensor.read().generation == 5
    assert sensor.read().generation == 5


def test_home_rejects_disconnection_without_confirming_zero():
    source = Mock()
    source.read.side_effect = [
        RollerReferenceState(True, False, 0, 1, 1),
        RollerReferenceState(False, False, 0, 1, 2),
    ]
    home = HomingService(RollerSensorService(source))
    home.start(now=0, position_turns=0)
    home.update(now=0.1, position_turns=-0.01)
    assert home.state == HomingState.ERROR
    assert 'disconnected' in home.error.lower()


def test_home_rejects_reconnected_sensor_with_new_generation():
    source = Mock()
    source.read.side_effect = [
        RollerReferenceState(True, False, 0, 1, 1),
        RollerReferenceState(True, True, 1, 2, 2),
    ]
    home = HomingService(RollerSensorService(source))
    home.start(now=0, position_turns=0)
    home.update(now=0.1, position_turns=-0.01)
    assert home.state == HomingState.ERROR
    assert 'connection changed' in home.error.lower()
