import pytest

from app.services.speed.settings import RuntimeSpeedSettings


def test_initial_values():
    settings = RuntimeSpeedSettings(
        belt_speed_percent=70,
        material_speed_percent=60,
        brush_speed_percent=90,
    )

    assert settings.belt_speed_percent == 70
    assert settings.material_speed_percent == 60
    assert settings.brush_speed_percent == 90


def test_brush_speed_can_be_none():
    settings = RuntimeSpeedSettings(
        belt_speed_percent=70,
        material_speed_percent=60,
        brush_speed_percent=None,
    )

    assert settings.brush_speed_percent is None


def test_belt_speed_can_be_changed():
    settings = RuntimeSpeedSettings(
        belt_speed_percent=70,
        material_speed_percent=60,
        brush_speed_percent=None,
    )

    settings.set_belt_speed(50)

    assert settings.belt_speed_percent == 50


def test_material_speed_can_be_changed():
    settings = RuntimeSpeedSettings(
        belt_speed_percent=70,
        material_speed_percent=60,
        brush_speed_percent=None,
    )

    settings.set_material_speed(80)

    assert settings.material_speed_percent == 80


def test_brush_speed_can_be_changed():
    settings = RuntimeSpeedSettings(
        belt_speed_percent=70,
        material_speed_percent=60,
        brush_speed_percent=90,
    )

    settings.set_brush_speed(40)

    assert settings.brush_speed_percent == 40


def test_brush_speed_can_be_disabled():
    settings = RuntimeSpeedSettings(
        belt_speed_percent=70,
        material_speed_percent=60,
        brush_speed_percent=90,
    )

    settings.set_brush_speed(None)

    assert settings.brush_speed_percent is None


@pytest.mark.parametrize("speed_percent", [0, -1, 101])
def test_invalid_belt_speed(speed_percent):
    with pytest.raises(ValueError):
        RuntimeSpeedSettings(
            belt_speed_percent=speed_percent,
            material_speed_percent=60,
            brush_speed_percent=None,
        )


@pytest.mark.parametrize("speed_percent", [0, -1, 101])
def test_invalid_material_speed(speed_percent):
    with pytest.raises(ValueError):
        RuntimeSpeedSettings(
            belt_speed_percent=70,
            material_speed_percent=speed_percent,
            brush_speed_percent=None,
        )


@pytest.mark.parametrize("speed_percent", [0, -1, 101])
def test_invalid_brush_speed(speed_percent):
    with pytest.raises(ValueError):
        RuntimeSpeedSettings(
            belt_speed_percent=70,
            material_speed_percent=60,
            brush_speed_percent=speed_percent,
        )
