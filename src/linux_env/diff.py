from dataclasses import dataclass
from pathlib import Path
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

    @property
    def changed(self) -> bool:
        return bool(self.added or self.removed)


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
    actual_dotfiles = {
        str(path.relative_to(dotfiles_root))
        for path in dotfiles_root.rglob("*")
        if path.is_file()
    } if dotfiles_root.exists() else set()
    sections.append(compare_sets("Dotfiles", expected_dotfiles, actual_dotfiles))

    system_changes = {}
    for key in ("distro", "version", "architecture", "desktop"):
        expected = manifest.system.get(key)
        actual = current.get(key)
        if expected and actual != expected:
            system_changes[key] = {"expected": expected, "actual": actual}

    return {"system": system_changes, "source": str(source)}, sections
