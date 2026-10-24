from abc import ABC, abstractmethod


class BaseDrive(ABC):
    @abstractmethod
    def set_frequency(self, frequency_hz: float) -> None:
        pass

    @abstractmethod
    def get_frequency(self) -> float:
        pass

    @abstractmethod
    def run_forward(self) -> None:
        pass

    @abstractmethod
    def run_reverse(self) -> None:
        pass

    @abstractmethod
    def stop(self) -> None:
        pass

    @abstractmethod
    def stop_coast(self) -> None:
        pass

    @abstractmethod
    def get_status(self) -> int:
        pass

    @abstractmethod
    def get_fault(self) -> int:
        pass

    @abstractmethod
    def reset_fault(self) -> None:
        pass
