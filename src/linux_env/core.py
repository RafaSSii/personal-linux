from pathlib import Path
import subprocess

from .detect import detect, distro_compatible
from .diff import compare_manifest_to_system
from .manifest import load_manifest, save_manifest
from .models import EnvironmentManifest
from .providers.apt import export_ppas, restore_commands as apt_repo_restore
from .providers.dotfiles import backup as backup_dotfiles
from .providers.dotfiles import restore_plan as dotfile_restore_plan
from .providers.flatpak import export_flatpaks
from .providers.flatpak import restore_commands as flatpak_restore
from .providers.packages import export_packages
from .providers.packages import installed_packages, restore_commands as package_restore
from .providers.packages import safe_restore_packages
from .providers.snap import export_snaps
from .providers.snap import restore_commands as snap_restore


def save_environment(destination: Path) -> EnvironmentManifest:
    destination.mkdir(parents=True, exist_ok=True)

    manager, packages = export_packages()
    package_key = "apt" if manager == "apt-get" else manager

    manifest = EnvironmentManifest(
        schema=2,
        system=detect(),
        packages={package_key: packages} if package_key else {},
        snap=export_snaps(),
        flatpaks=export_flatpaks(),
        repositories={"apt_ppas": export_ppas()} if manager == "apt-get" else {},
    )
    manifest.dotfiles = backup_dotfiles(destination / "dotfiles")
    save_manifest(manifest, destination / "manifest.yaml")
    return manifest


def _restore_package_manager(manager: str, packages: list[str]) -> list[list[str]]:
    return package_restore("apt-get" if manager == "apt" else manager, packages)


def _validate_restore_manifest(manifest, target) -> None:
    if not distro_compatible(manifest.system, target):
        raise RuntimeError(
            "This manifest was created on "
            f"{manifest.system.get('distro', 'unknown')} and this restore target "
            f"is {target.get('distro', 'unknown')}. These distributions are not "
            "currently considered compatible."
        )


def plan_restore(source: Path) -> tuple[list[list[str]], dict[str, list[str]], list[str]]:
    """Plan a conservative restore: install missing portable packages and protect dotfiles."""
    manifest = load_manifest(source / "manifest.yaml")
    target = detect()
    _validate_restore_manifest(manifest, target)

    commands: list[list[str]] = []
    report: dict[str, list[str]] = {
        "already_installed": [],
        "skipped_boot": [],
        "skipped_hardware": [],
        "skipped_distribution": [],
        "to_install": [],
    }

    current_manager, _ = export_packages()
    for manifest_manager, packages in manifest.packages.items():
        normalized = "apt-get" if manifest_manager == "apt" else manifest_manager
        if current_manager and normalized != current_manager:
            report["skipped_distribution"].extend(packages)
            continue

        portable, skipped = safe_restore_packages(packages)
        for category in ("boot", "hardware", "distribution"):
            report[f"skipped_{category}"].extend(skipped.get(category, []))

        installed = installed_packages(normalized)
        missing = [package for package in portable if package not in installed]
        report["already_installed"].extend(
            package for package in portable if package in installed
        )
        report["to_install"].extend(missing)
        commands += _restore_package_manager(normalized, missing)

    commands += apt_repo_restore(manifest.repositories.get("apt_ppas", []))

    installed_snaps = {
        item.get("name") for item in export_snaps()
        if isinstance(item, dict) and item.get("name")
    }
    missing_snaps = [
        item for item in manifest.snap
        if (
            (item.get("name") if isinstance(item, dict) else item)
            and (item.get("name") if isinstance(item, dict) else item) not in installed_snaps
        )
    ]
    commands += snap_restore(missing_snaps)

    installed_flatpaks = {
        item.get("app_id") for item in export_flatpaks()
        if isinstance(item, dict) and item.get("app_id")
    }
    missing_flatpaks = [
        item for item in manifest.flatpaks
        if (
            (item.get("app_id") if isinstance(item, dict) else item)
            and (item.get("app_id") if isinstance(item, dict) else item) not in installed_flatpaks
        )
    ]
    commands += flatpak_restore(missing_flatpaks)

    dotfile_commands, conflicts = dotfile_restore_plan(source)
    commands += dotfile_commands
    for key in report:
        report[key] = sorted(set(report[key]))
    return commands, report, conflicts


def restore_environment(
    source: Path,
    dry_run: bool = False,
    *,
    assume_yes: bool = False,
    confirm=None,
) -> list[list[str]]:
    commands, _report, conflicts = plan_restore(source)
    if conflicts and not dry_run and not assume_yes:
        if confirm is None or not confirm():
            raise RuntimeError(
                "Restore cancelled: existing dotfiles would be overwritten. "
                "Review the dry-run; existing files are backed up before replacement."
            )

    if not dry_run:
        for command in commands:
            subprocess.run(command, check=True)

    return commands


def _remove_commands(manager: str, packages: list[str]) -> list[list[str]]:
    if not packages:
        return []
    if manager in ("apt", "apt-get"):
        return [["sudo", "apt-get", "remove", "-y", *packages]]
    if manager == "dnf":
        return [["sudo", "dnf", "remove", "-y", *packages]]
    if manager == "pacman":
        return [["sudo", "pacman", "-R", "--noconfirm", *packages]]
    if manager == "zypper":
        return [["sudo", "zypper", "remove", "-y", *packages]]
    return []


def _snap_remove_commands(names: list[str]) -> list[list[str]]:
    return [["sudo", "snap", "remove", name] for name in names]


def _flatpak_remove_commands(app_ids: list[str]) -> list[list[str]]:
    return [["flatpak", "uninstall", "-y", app_id] for app_id in app_ids]


def _ppa_remove_commands(ppas: list[str]) -> list[list[str]]:
    return [
        ["sudo", "add-apt-repository", "--remove", "-y", ppa]
        for ppa in ppas
        if ppa.startswith("ppa:")
    ]


def _dotfile_restore_commands(source: Path, paths: list[str]) -> list[list[str]]:
    commands, _ = dotfile_restore_plan(source, paths=paths)
    return commands


def plan_apply(source: Path) -> tuple[list[list[str]], list[list[str]]]:
    manifest = load_manifest(source / "manifest.yaml")
    target = detect()

    if not distro_compatible(manifest.system, target):
        raise RuntimeError(
            "This manifest was created on "
            f"{manifest.system.get('distro', 'unknown')} and this apply target "
            f"is {target.get('distro', 'unknown')}. These distributions are not "
            "currently considered compatible."
        )

    metadata, sections = compare_manifest_to_system(source)
    del metadata

    sections_by_name = {section.name: section for section in sections}
    commands: list[list[str]] = []
    destructive: list[list[str]] = []

    manager, _ = export_packages()
    if manager:
        section_name = {
            "apt-get": "APT packages",
            "dnf": "DNF packages",
            "pacman": "Pacman packages",
            "zypper": "Zypper packages",
        }.get(manager, "Packages")
        package_section = sections_by_name[section_name]
        manager_name = "apt-get" if manager == "apt-get" else manager
        commands += _restore_package_manager(manager_name, package_section.removed)
        destructive += _remove_commands(manager_name, package_section.added)

    snap_section = sections_by_name["Snap"]
    expected_snaps = {
        item.get("name"): item
        for item in manifest.snap
        if isinstance(item, dict) and item.get("name")
    }
    commands += snap_restore(
        [expected_snaps[name] for name in snap_section.removed]
    )
    destructive += _snap_remove_commands(snap_section.added)

    flatpak_section = sections_by_name["Flatpak"]
    expected_flatpaks = {
        item.get("app_id"): item
        for item in manifest.flatpaks
        if isinstance(item, dict) and item.get("app_id")
    }
    commands += flatpak_restore(
        [expected_flatpaks[app_id] for app_id in flatpak_section.removed]
    )
    destructive += _flatpak_remove_commands(flatpak_section.added)

    ppa_section = sections_by_name["APT PPAs"]
    commands += apt_repo_restore(ppa_section.removed)
    destructive += _ppa_remove_commands(ppa_section.added)

    dotfile_section = sections_by_name["Dotfiles"]
    commands += _dotfile_restore_commands(source, dotfile_section.removed)
    destructive += _dotfile_restore_commands(source, dotfile_section.modified)

    return commands, destructive


def apply_environment(
    source: Path,
    *,
    dry_run: bool = False,
    assume_yes: bool = False,
    confirm=None,
) -> list[list[str]]:
    commands, destructive = plan_apply(source)

    if dry_run:
        return commands + destructive

    if destructive and not assume_yes:
        if confirm is None:
            confirm = lambda: False
        if not confirm():
            raise RuntimeError(
                "Apply cancelled: destructive changes require confirmation."
            )

    for command in commands + destructive:
        subprocess.run(command, check=True)

    return commands + destructive
