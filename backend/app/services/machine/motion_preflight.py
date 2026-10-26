"""Fault-only preflight for a motion command (not a safety certification).

Unlike the read-only readiness snapshot, this deliberately permits already
running drives. It never sends RESET or movement commands.
"""


def require_motion_fault_free(drives) -> None:
    for name, drive in drives:
        try:
            fault = drive.get_fault()
        except Exception as exc:
            raise RuntimeError(f"Motion blocked: {name} fault telemetry unavailable") from exc
        if type(fault) is not int or not 0 <= fault <= 0xFFFF:
            raise RuntimeError(f"Motion blocked: {name} invalid fault telemetry")
        if fault:
            raise RuntimeError(f"Motion blocked: {name} VFD fault {fault}")
