"""Read-only recovery verification for a latched VFD fault.

This component deliberately does not clear software latches. The final
acknowledgement must coordinate all session owners and the polling runtime.
"""

import math
import logging

logger = logging.getLogger(__name__)
from dataclasses import dataclass


@dataclass(frozen=True)
class RecoveryVerification:
    drive_ids: tuple[int, ...]
    consecutive_stop_samples: int
    verified: bool = True


class MotionFaultRecoveryService:
    def __init__(self, machine, drive_service, auto_service, calibration_service, homing_service):
        self.machine = machine
        self.drive_service = drive_service
        self.auto_service = auto_service
        self.calibration_service = calibration_service
        self.homing_service = homing_service

    def verify(self, *, operator_confirmed_stopped: bool) -> RecoveryVerification:
        """Verify recovery prerequisites without changing state or sending commands.

        A successful result is NOT permission to move or clear a latch.
        """
        if operator_confirmed_stopped is not True:
            raise RuntimeError("Operator must confirm mechanical stop after physical RESET")
        if self.machine.motion_fault_latched is None:
            raise RuntimeError("No machine motion fault is latched")
        auto_status = self.auto_service.get_status()
        if auto_status.get("running") or auto_status.get("paused") or auto_status.get("status") not in ("FAULT", "IDLE"):
            raise RuntimeError("AUTO session is not inactive")
        if self.calibration_service.active or self.calibration_service.auto_mode is not None:
            raise RuntimeError("CALIBRATION session is active")
        home_status = self.homing_service.get_status()
        if home_status.get("searching") or home_status.get("awaiting_stop") or home_status.get("state") in ("SEARCHING", "STOPPING"):
            raise RuntimeError("HOME is active")

        drives = self.drive_service.drives
        configs = self.drive_service.configs
        expected = (1, 2, 3)
        if any(drive_id not in drives or drive_id not in configs or not configs[drive_id].enabled for drive_id in expected):
            raise RuntimeError("All three GAIN drives must be configured and enabled")
        for sample in range(3):
            for drive_id in expected:
                drive = drives[drive_id]
                readings = {}
                for name, getter in (("fault", drive.get_fault),
                                     ("status", drive.get_status),
                                     ("frequency", drive.get_frequency)):
                    logger.info("Recovery sample %d/3 drive %d reading %s", sample + 1, drive_id, name)
                    try:
                        readings[name] = getter()
                    except Exception as exc:
                        logger.exception("Recovery telemetry failed: drive %d %s", drive_id, name)
                        raise RuntimeError(
                            f"Drive {drive_id}: {name} telemetry unavailable"
                        ) from exc
                fault, status, frequency = (readings[k] for k in ("fault", "status", "frequency"))
                if type(fault) is not int or fault != 0:
                    raise RuntimeError(f"Drive {drive_id}: fault not cleared or invalid")
                if type(status) is not int or status != 3:
                    raise RuntimeError(f"Drive {drive_id}: STOP not confirmed")
                if (type(frequency) not in (int, float) or not math.isfinite(frequency)
                        or frequency != 0):
                    raise RuntimeError(f"Drive {drive_id}: zero frequency not confirmed")
        return RecoveryVerification(expected, 3)

    def acknowledge(self, *, operator_confirmed_stopped: bool) -> RecoveryVerification:
        """Coordinated software-only recovery; never commands a VFD.

        The machine latch remains in force through verification and cleanup.
        This must be invoked under MotionFaultRuntime's polling exclusion.
        """
        # The global motion latch remains set during read-only Modbus verification.
        # Never hold the machine state RLock over 27 potentially slow serial reads.
        result = self.verify(operator_confirmed_stopped=operator_confirmed_stopped)
        with self.machine._roller_lock:
            if self.machine._motion_fault_latched is None:
                raise RuntimeError("Motion fault latch changed during recovery")
            if self.machine._roller_stop_fault or self.machine._external_stop_pending:
                raise RuntimeError("Roller STOP fault/pending notification must be resolved separately")
            if self.machine.roller_owner not in (None, self.homing_service.OWNER):
                raise RuntimeError("Roller owned by another session")
            if self.auto_service._prepared is not None:
                raise RuntimeError("AUTO prepared session must be stopped")
            # Cleanup methods are software-only and cannot send RUN/STOP.
            # Global latch is cleared last; failures retain movement blocking.
            self.homing_service.complete_motion_fault_recovery()
            self.auto_service.complete_motion_fault_recovery()
            self.calibration_service.complete_motion_fault_recovery()
            self.machine.complete_motion_fault_recovery()
            return result
