from dataclasses import dataclass
from pathlib import Path
import hashlib
from typing import Any

from .detect import detect
from .manifest import load_manifest
from .providers.apt import export_ppas
from .providers.flatpak import export_flatpaks
from .providers.packages import export_packages
from .providers.snap import export_snaps


@dataclass
class DiffSection:
    name: str
    added: list[str]
    removed: list[str]
    modified: list[str] | None = None

    def __post_init__(self) -> None:
        if self.modified is None:
            self.modified = []

    @property
    def changed(self) -> bool:
        return bool(self.added or self.removed or self.modified)


def _names(items: list[Any], key: str) -> set[str]:
    result = set()
    for item in items:
        if isinstance(item, str):
            result.add(item)
        elif item.get(key):
            result.add(item[key])
    return result


def compare_sets(name: str, expected: set[str], actual: set[str]) -> DiffSection:
    return DiffSection(
        name=name,
        added=sorted(actual - expected),
        removed=sorted(expected - actual),
    )


def _sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def compare_manifest_to_system(source: Path) -> tuple[dict[str, Any], list[DiffSection]]:
    manifest = load_manifest(source / "manifest.yaml")
    current = detect()
    sections: list[DiffSection] = []

    expected_apt = set(manifest.packages.get("apt", []))
    manager, current_packages = export_packages()
    actual_apt = set(current_packages) if manager == "apt-get" else set()
    sections.append(compare_sets("APT packages", expected_apt, actual_apt))

    expected_snap = _names(manifest.snap, "name")
    actual_snap = _names(export_snaps(), "name")
    sections.append(compare_sets("Snap", expected_snap, actual_snap))

    expected_flatpak = _names(manifest.flatpaks, "app_id")
    actual_flatpak = _names(export_flatpaks(), "app_id")
    sections.append(compare_sets("Flatpak", expected_flatpak, actual_flatpak))

    expected_ppas = set(manifest.repositories.get("apt_ppas", []))
    actual_ppas = set(export_ppas()) if manager == "apt-get" else set()
    sections.append(compare_sets("APT PPAs", expected_ppas, actual_ppas))

    expected_dotfiles = set(manifest.dotfiles)
    dotfiles_root = source / "dotfiles"
    actual_dotfiles = set()
    modified_dotfiles = []

    for relative in expected_dotfiles:
        backup = dotfiles_root / relative
        current_file = Path.home() / relative

        if not current_file.exists():
            continue
        actual_dotfiles.add(relative)

        if _sha256(backup) != _sha256(current_file):
            modified_dotfiles.append(relative)

    missing = expected_dotfiles - actual_dotfiles
    sections.append(
        DiffSection(
            name="Dotfiles",
            added=[],
            removed=sorted(missing),
            modified=sorted(modified_dotfiles),
        )
    )

    system_changes = {}
    for key in ("distro", "version", "architecture", "desktop"):
        expected = manifest.system.get(key)
        actual = current.get(key)
        if expected and actual != expected:
            system_changes[key] = {"expected": expected, "actual": actual}

    return {"system": system_changes, "source": str(source)}, sections
