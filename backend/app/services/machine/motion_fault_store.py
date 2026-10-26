"""Durable, fail-closed motion-fault acknowledgement state for REAL mode.

The file must reside on persistent storage. Missing/invalid state requires an
operator acknowledgement; it is never interpreted as a clean startup.
"""
import json
import os
import tempfile
from pathlib import Path


class MotionFaultStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def read_latch(self) -> str | None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or data.get("version") != 1:
                raise ValueError("invalid version")
            if data.get("acknowledged") is True and data.get("reason") is None:
                return None
            if data.get("acknowledged") is False and isinstance(data.get("reason"), str) and data["reason"]:
                return data["reason"]
            raise ValueError("invalid state")
        except (OSError, ValueError, TypeError):
            return "Motion blocked: persistent recovery state missing or invalid"

    def write_latch(self, reason: str | None) -> None:
        """Atomic replace and fsync. Any failure must leave the caller blocked."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(prefix=".motion-fault-", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump({"version": 1, "acknowledged": reason is None, "reason": reason}, stream)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_path, self.path)
            directory_fd = os.open(self.path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
