class RollerPositionTracker:
    """
    Tracks roller position relative to a calibration zero point

    Forward rotation increases the position.
    Rewerse rotation decreases the position.
    """

    def __init__(self):
        self._position_turns = 0.0

    @property
    def position_turns(self) -> float:
        return self._position_turns

    def move_forward(self, revolutions: float) -> None:
        self._validate_revolutions(revolutions)
        self._position_turns += revolutions

    def move_reverse(self, revolutions: float) -> None:
        self._validate_revolutions(revolutions)
        self._position_turns -= revolutions

    def reset(self) -> None:
        self._position_turns = 0.0

    @staticmethod
    def _validate_revolutions(revolutions: float) -> None:
        if revolutions < 0:
            raise ValueError("Revolutions cannot be negative")
