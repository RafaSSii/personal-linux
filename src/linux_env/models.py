from dataclasses import dataclass, field
from typing import Any

@dataclass
class EnvironmentManifest:
    schema: int = 1
    system: dict[str, Any] = field(default_factory=dict)
    packages: dict[str, list[str]] = field(default_factory=dict)
    dotfiles: list[str] = field(default_factory=list)
    flatpaks: list[str] = field(default_factory=list)
