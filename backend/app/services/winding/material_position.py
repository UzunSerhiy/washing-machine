from enum import Enum


class MaterialPositionState(str, Enum):
    BELT_BEFORE_MATERIAL = "belt_before_material"
    MATERIAL = "material"
    MATERIAL_END = "material_end"
    BRUSH_CLEAR = "brush_clear"
    CYCLE_END = "cycle_end"


class MaterialPositionTracker:
    """
    Отслеживает логическое положение материала
    относительно зон цикла.

    Физические обороты ролика сюда приходят уже рассчитанными
    RollerRotationCounter.

    Этот класс не знает о VFD и не считает физические обороты.
    """

    def __init__(
        self,
        belt_start_turns: float,
        material_turns: float,
        brush_clear_turns: float,
    ):
        if belt_start_turns < 0:
            raise ValueError("Belt start turns cannot be negative")

        if material_turns <= 0:
            raise ValueError("Material turns must be greater than zero")

        if brush_clear_turns < 0:
            raise ValueError("Brush clear turns cannot be negative")

        self.belt_start_turns = belt_start_turns
        self.material_turns = material_turns
        self.brush_clear_turns = brush_clear_turns

        self.total_length_turns = belt_start_turns + material_turns + brush_clear_turns

        self._position_turns = 0.0

    @property
    def position_turns(self) -> float:
        return self._position_turns

    @property
    def state(self) -> MaterialPositionState:
        if self._position_turns < self.belt_start_turns:
            return MaterialPositionState.BELT_BEFORE_MATERIAL

        material_end = self.belt_start_turns + self.material_turns

        if self._position_turns < material_end:
            return MaterialPositionState.MATERIAL

        if self._position_turns < self.total_length_turns:
            return MaterialPositionState.BRUSH_CLEAR

        return MaterialPositionState.CYCLE_END

    def move_forward(self, turns: float) -> MaterialPositionState:
        self._validate_turns(turns)

        self._position_turns += turns

        if self._position_turns > self.total_length_turns:
            self._position_turns = self.total_length_turns

        return self.state

    def move_reverse(self, turns: float) -> MaterialPositionState:
        self._validate_turns(turns)

        self._position_turns -= turns

        if self._position_turns < 0:
            self._position_turns = 0.0

        return self.state

    def reset(self) -> None:
        self._position_turns = 0.0

    @staticmethod
    def _validate_turns(turns: float) -> None:
        if turns < 0:
            raise ValueError("Turns cannot be negative")
