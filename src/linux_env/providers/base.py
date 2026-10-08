from abc import ABC, abstractmethod
from typing import Any

class Provider(ABC):
    @abstractmethod
    def detect(self) -> Any: ...
    @abstractmethod
    def export(self) -> Any: ...
    @abstractmethod
    def restore_commands(self, data: Any) -> list[list[str]]: ...
