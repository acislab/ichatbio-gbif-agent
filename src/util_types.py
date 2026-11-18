from enum import Enum


class ParameterEnum(Enum):
    def __str__(self) -> str:
        return str(self.value)
