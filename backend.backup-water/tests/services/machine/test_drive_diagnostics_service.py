import pytest

from app.services.machine.drive_diagnostics_service import (
    DriveDiagnosticsService,
)

from app.services.machine.drive_status import (
    DriveStatus,
    MachineDrivesStatus,
)


class FakeDiagnosticsProvider:
    def are_drives_ready(self) -> bool:
        return False


class FakeReadyDiagnosticsProvider:
    def are_drives_ready(self) -> bool:
        return True


def test_drive_diagnostics_rejects_missing_provider():
    service = DriveDiagnosticsService()

    with pytest.raises(RuntimeError, match="diagnostics"):
        service.require_drives_ready()


def test_drive_diagnostics_rejects_unready_drives():
    provider = FakeDiagnosticsProvider()

    service = DriveDiagnosticsService(
        diagnostics_provider=provider,
    )

    with pytest.raises(RuntimeError, match="diagnostics"):
        service.require_drives_ready()


def test_drive_diagnostics_accepts_ready_drives():
    provider = FakeReadyDiagnosticsProvider()

    service = DriveDiagnosticsService(
        diagnostics_provider=provider,
    )

    assert service.require_drives_ready() is None


def test_drive_diagnostics_handles_provider_exception():
    class FailingDiagnosticsProvider:
        def are_drives_ready(self) -> bool:
            raise OSError("RS-485 communication lost")

    service = DriveDiagnosticsService(
        diagnostics_provider=FailingDiagnosticsProvider(),
    )

    with pytest.raises(
        RuntimeError,
        match="diagnostics provider check failed",
    ) as exc_info:
        service.require_drives_ready()

    assert isinstance(exc_info.value.__cause__, OSError)


def test_drive_diagnostics_rejects_disconnected_roller():
    class FakeDiagnosticsProvider:
        def get_drives_status(self) -> MachineDrivesStatus:
            return MachineDrivesStatus(
                roller=DriveStatus(
                    connected=False,
                    faulted=False,
                    running=False,
                    frequency_hz=0.0,
                ),
                brushes=DriveStatus(
                    connected=True,
                    faulted=False,
                    running=False,
                    frequency_hz=0.0,
                ),
            )

    service = DriveDiagnosticsService(
        diagnostics_provider=FakeDiagnosticsProvider(),
    )

    with pytest.raises(
        RuntimeError,
        match="roller.*communication",
    ):
        service.require_drives_ready()


def test_drive_diagnostics_rejects_disconnected_brushes():
    class FakeDiagnosticsProvider:
        def get_drives_status(self) -> MachineDrivesStatus:
            return MachineDrivesStatus(
                roller=DriveStatus(
                    connected=True,
                    faulted=False,
                    running=False,
                    frequency_hz=0.0,
                ),
                brushes=DriveStatus(
                    connected=False,
                    faulted=False,
                    running=False,
                    frequency_hz=0.0,
                ),
            )

    service = DriveDiagnosticsService(
        diagnostics_provider=FakeDiagnosticsProvider(),
    )

    with pytest.raises(
        RuntimeError,
        match="brushes.*communication",
    ):
        service.require_drives_ready()


def test_drive_diagnostics_rejects_faulted_roller():
    class FakeDiagnosticsProvider:
        def get_drives_status(self) -> MachineDrivesStatus:
            return MachineDrivesStatus(
                roller=DriveStatus(
                    connected=True,
                    faulted=True,
                    running=False,
                    frequency_hz=0.0,
                ),
                brushes=DriveStatus(
                    connected=True,
                    faulted=False,
                    running=False,
                    frequency_hz=0.0,
                ),
            )

    service = DriveDiagnosticsService(
        diagnostics_provider=FakeDiagnosticsProvider(),
    )

    with pytest.raises(
        RuntimeError,
        match="roller.*fault",
    ):
        service.require_drives_ready()


def test_drive_diagnostics_rejects_faulted_brushes():
    class FakeDiagnosticsProvider:
        def get_drives_status(self) -> MachineDrivesStatus:
            return MachineDrivesStatus(
                roller=DriveStatus(
                    connected=True,
                    faulted=False,
                    running=False,
                    frequency_hz=0.0,
                ),
                brushes=DriveStatus(
                    connected=True,
                    faulted=True,
                    running=False,
                    frequency_hz=0.0,
                ),
            )

    service = DriveDiagnosticsService(
        diagnostics_provider=FakeDiagnosticsProvider(),
    )

    with pytest.raises(
        RuntimeError,
        match="brushes.*fault",
    ):
        service.require_drives_ready()


@pytest.mark.parametrize(
    "drive, changes, error",
    [
        ("roller", {"connected": False}, "roller.*communication"),
        ("brushes", {"connected": False}, "brushes.*communication"),
        ("roller", {"faulted": True}, "roller.*fault"),
        ("brushes", {"faulted": True}, "brushes.*fault"),
        ("roller", {"running": True}, "roller.*running"),
        ("brushes", {"running": True}, "brushes.*running"),
        ("roller", {"frequency_hz": 10.0}, "roller.*frequency"),
        ("brushes", {"frequency_hz": 10.0}, "brushes.*frequency"),
        ("roller", {"frequency_hz": -1.0}, "roller.*frequency"),
        ("brushes", {"frequency_hz": -1.0}, "brushes.*frequency"),
        ("roller", {"frequency_hz": float("nan")}, "roller.*frequency"),
        ("brushes", {"frequency_hz": float("nan")}, "brushes.*frequency"),
        ("roller", {"frequency_hz": float("inf")}, "roller.*frequency"),
        ("brushes", {"frequency_hz": float("inf")}, "brushes.*frequency"),
    ],
)
def test_drive_diagnostics_rejects_invalid_drive_state(
    drive,
    changes,
    error,
):
    def make_status(name):
        values = {
            "connected": True,
            "faulted": False,
            "running": False,
            "frequency_hz": 0.0,
        }

        if name == drive:
            values.update(changes)

        return DriveStatus(**values)

    class FakeDiagnosticsProvider:
        def get_drives_status(self):
            return MachineDrivesStatus(
                roller=make_status("roller"),
                brushes=make_status("brushes"),
            )

    service = DriveDiagnosticsService(
        diagnostics_provider=FakeDiagnosticsProvider(),
    )

    with pytest.raises(RuntimeError, match=error):
        service.require_drives_ready()


def test_drive_diagnostics_accepts_both_stopped_drives():
    class FakeDiagnosticsProvider:
        def get_drives_status(self):
            return MachineDrivesStatus(
                roller=DriveStatus(
                    connected=True,
                    faulted=False,
                    running=False,
                    frequency_hz=0.0,
                ),
                brushes=DriveStatus(
                    connected=True,
                    faulted=False,
                    running=False,
                    frequency_hz=0.0,
                ),
            )

    service = DriveDiagnosticsService(
        diagnostics_provider=FakeDiagnosticsProvider(),
    )

    assert service.require_drives_ready() is None


def test_drive_diagnostics_rejects_invalid_response():
    class FakeDiagnosticsProvider:
        def get_drives_status(self):
            return None

    service = DriveDiagnosticsService(
        diagnostics_provider=FakeDiagnosticsProvider(),
    )

    with pytest.raises(RuntimeError, match="invalid drive diagnostics"):
        service.require_drives_ready()
