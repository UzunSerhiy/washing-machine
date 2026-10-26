"""Read-only VFD readiness snapshot; not a motion interlock."""

import math


def get_readiness_snapshot(drive_service, homing_service):
    drives = []
    reasons = []
    for drive_id, config in sorted(drive_service.configs.items()):
        if not config.enabled:
            continue
        entry = {"drive_id": drive_id, "name": config.name, "type": config.type,
                 "connected": False, "status": None, "frequency_hz": None,
                 "fault": None, "ready": False, "reasons": []}
        drive = drive_service.drives.get(drive_id)
        if drive is None:
            entry["reasons"].append("DRIVE_NOT_CONFIGURED")
        else:
            try:
                fault = drive.get_fault()
                status = drive.get_status()
                frequency = drive.get_frequency()
                if type(fault) is not int or not 0 <= fault <= 65535:
                    raise ValueError("invalid fault register")
                if type(status) is not int or status not in (1, 2, 3):
                    raise ValueError("invalid status register")
                if (isinstance(frequency, bool) or not isinstance(frequency, (int, float))
                        or not math.isfinite(frequency) or frequency < 0):
                    raise ValueError("invalid frequency")
                entry.update(connected=True, status=status, frequency_hz=frequency, fault=fault)
                if fault:
                    entry["reasons"].append("VFD_EXTERNAL_FAULT" if fault == 15 else "VFD_FAULT")
                if status != 3 or frequency != 0:
                    entry["reasons"].append("DRIVE_NOT_STOPPED")
            except Exception:
                entry["reasons"].append("VFD_TELEMETRY_UNAVAILABLE")
        entry["ready"] = not entry["reasons"]
        reasons.extend(f"drive_{drive_id}:{reason}" for reason in entry["reasons"])
        drives.append(entry)
    if not drives:
        reasons.append("NO_ENABLED_DRIVES")
    home = homing_service.get_status()
    if home.get("faulted"):
        reasons.append("HOME_FAULT_LATCHED")
    return {"ready": not reasons, "reasons": reasons, "drives": drives,
            "home_faulted": bool(home.get("faulted")),
            "diagnostic_only": True}
