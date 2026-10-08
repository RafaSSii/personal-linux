from dataclasses import dataclass, field
from typing import Any


@dataclass
class EnvironmentManifest:
    schema: int = 2
    system: dict[str, Any] = field(default_factory=dict)
    packages: dict[str, list[str]] = field(default_factory=dict)
    snap: list[dict[str, Any]] = field(default_factory=list)
    flatpaks: list[Any] = field(default_factory=list)
    repositories: dict[str, list[str]] = field(default_factory=dict)
    dotfiles: list[str] = field(default_factory=list)
