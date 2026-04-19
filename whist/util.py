from enum import Enum, auto
from typing import Any

__all__ = ["OrderedEnum", "auto"]


class OrderedEnum(Enum):
    """See https://docs.python.org/3/library/enum.html#orderedenum."""

    def __ge__(self, other: Any) -> bool:
        if self.__class__ is other.__class__:
            return bool(self.value >= other.value)
        return NotImplemented

    def __gt__(self, other: Any) -> bool:
        if self.__class__ is other.__class__:
            return bool(self.value > other.value)
        return NotImplemented

    def __le__(self, other: Any) -> bool:
        if self.__class__ is other.__class__:
            return bool(self.value <= other.value)
        return NotImplemented

    def __lt__(self, other: Any) -> bool:
        if self.__class__ is other.__class__:
            return bool(self.value < other.value)
        return NotImplemented
