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

    def set_position(self, position_turns: float) -> None:
        if position_turns < 0:
            raise ValueError("Position cannot be negative")

        self._position_turns = position_turns

    def move_forward(self, revolutions: float) -> None:
        self._validate_revolutions(revolutions)
        self._position_turns += revolutions

    def move_reverse(
        self,
        revolutions: float,
        allow_negative: bool = False,
    ) -> None:
        self._validate_revolutions(revolutions)

        new_position = self._position_turns - revolutions

        if allow_negative:
            self._position_turns = new_position
        else:
            self._position_turns = max(0.0, new_position)

    def reset(self) -> None:
        self._position_turns = 0.0

    @staticmethod
    def _validate_revolutions(revolutions: float) -> None:
        if revolutions < 0:
            raise ValueError("Revolutions cannot be negative")
