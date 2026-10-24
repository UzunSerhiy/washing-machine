from typing import Protocol


class SafetyProvider(Protocol):
    def is_safe(self) -> bool: ...


class MachineSafetyService:
    def __init__(
        self,
        safety_provider: SafetyProvider | None = None,
    ) -> None:
        self.safety_provider = safety_provider

    def require_safe_state(self) -> None:
        if self.safety_provider is None:
            raise RuntimeError("Cannot reset fault: safety provider is not configured")

        try:
            is_safe = self.safety_provider.is_safe()

        except Exception as exc:
            raise RuntimeError(
                "Cannot reset fault: safety provider check failed"
            ) from exc

        if not is_safe:
            raise RuntimeError("Cannot reset fault: safety state is not confirmed")
