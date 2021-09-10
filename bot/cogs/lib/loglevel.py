from enum import Enum
class LogLevel(Enum):
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    FATAL = 99
    def __ge__(self, other):
        if self.__class__ is other.__class__:
           return self.value >= other.value
        return NotImplemented
    def __gt__(self, other):
        if self.__class__ is other.__class__:
           return self.value > other.value
        return NotImplemented
    def __le__(self, other):
        if self.__class__ is other.__class__:
           return self.value < other.value
        return NotImplemented

    def __lt__(self, other):
        if self.__class__ is other.__class__:
           return self.value < other.value
        return NotImplemented
    def __eq__(self, other):
        if self.__class__ is other.__class__:
           return self.value == other.value
        return NotImplemented
