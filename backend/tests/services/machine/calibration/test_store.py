import pytest

from app.services.machine.calibration.points import CalibrationPoint
from app.services.machine.calibration.store import CalibrationPointStore


def test_store_is_empty_initially():
    store = CalibrationPointStore()

    assert store.is_empty()


def test_set_and_get_point():
    store = CalibrationPointStore()

    store.set(
        CalibrationPoint.WINDING_BELT_START,
        12.5,
    )

    assert store.get(CalibrationPoint.WINDING_BELT_START) == 12.5


def test_get_unknown_point_returns_none():
    store = CalibrationPointStore()

    assert store.get(CalibrationPoint.WINDING_BELT_START) is None


def test_has_point():
    store = CalibrationPointStore()

    store.set(
        CalibrationPoint.WASHING_BELT_SAFE,
        25.0,
    )

    assert store.has(CalibrationPoint.WASHING_BELT_SAFE)


def test_overwrite_point():
    store = CalibrationPointStore()

    point = CalibrationPoint.WINDING_BELT_START

    store.set(point, 10.0)
    store.set(point, 15.0)

    assert store.get(point) == 15.0


def test_clear_point():
    store = CalibrationPointStore()

    point = CalibrationPoint.WINDING_BELT_START

    store.set(point, 10.0)
    store.clear(point)

    assert store.get(point) is None
    assert not store.has(point)


def test_clear_all():
    store = CalibrationPointStore()

    store.set(
        CalibrationPoint.WINDING_BELT_START,
        10.0,
    )
    store.set(
        CalibrationPoint.WINDING_MATERIAL_WOUND,
        30.0,
    )

    store.clear_all()

    assert store.is_empty()


def test_negative_turns_are_rejected():
    store = CalibrationPointStore()

    with pytest.raises(ValueError, match="Turns cannot be negative"):
        store.set(
            CalibrationPoint.WINDING_BELT_START,
            -1.0,
        )
