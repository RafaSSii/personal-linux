from pathlib import Path
import subprocess

from .detect import detect
from .diff import compare_manifest_to_system
from .manifest import load_manifest, save_manifest
from .models import EnvironmentManifest
from .providers.apt import export_ppas, restore_commands as apt_repo_restore
from .providers.dotfiles import backup as backup_dotfiles
from .providers.dotfiles import restore_commands as dotfile_restore
from .providers.flatpak import export_flatpaks
from .providers.flatpak import restore_commands as flatpak_restore
from .providers.packages import export_packages
from .providers.packages import restore_commands as package_restore
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


def restore_environment(source: Path, dry_run: bool = False) -> list[list[str]]:
    manifest = load_manifest(source / "manifest.yaml")
    target = detect()

    source_distro = manifest.system.get("distro", "")
    if source_distro == "ubuntu" and target.get("distro") != "ubuntu":
        raise RuntimeError(
            "This manifest was created on Ubuntu and this restore target "
            f"is {target.get('distro', 'unknown')}. Run the restore on Ubuntu."
        )

    commands = []
    commands += apt_repo_restore(manifest.repositories.get("apt_ppas", []))

    for manager, packages in manifest.packages.items():
        commands += _restore_package_manager(manager, packages)

    commands += snap_restore(manifest.snap)
    commands += flatpak_restore(manifest.flatpaks)

    if manifest.dotfiles:
        commands += dotfile_restore(source)

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
    root = source / "dotfiles"
    home = Path.home()
    return [
        ["cp", "-a", str(root / relative), str(home / relative)]
        for relative in paths
        if (root / relative).exists()
    ]


def plan_apply(source: Path) -> tuple[list[list[str]], list[list[str]]]:
    manifest = load_manifest(source / "manifest.yaml")
    target = detect()

    source_distro = manifest.system.get("distro", "")
    if source_distro == "ubuntu" and target.get("distro") != "ubuntu":
        raise RuntimeError(
            "This manifest was created on Ubuntu and this apply target "
            f"is {target.get('distro', 'unknown')}. Run apply on Ubuntu."
        )

    metadata, sections = compare_manifest_to_system(source)
    del metadata

    sections_by_name = {section.name: section for section in sections}
    commands: list[list[str]] = []
    destructive: list[list[str]] = []

    manager, _ = export_packages()
    if manager:
        apt_section = sections_by_name["APT packages"]
        manager_name = "apt-get" if manager == "apt-get" else manager
        commands += _restore_package_manager(
            manager_name, apt_section.removed
        )
        destructive += _remove_commands(manager_name, apt_section.added)

    snap_section = sections_by_name["Snap"]
    commands += snap_restore(
        [{"name": name} for name in snap_section.removed]
    )
    destructive += _snap_remove_commands(snap_section.added)

    flatpak_section = sections_by_name["Flatpak"]
    commands += flatpak_restore(
        [{"app_id": app_id, "remote": "flathub"}
         for app_id in flatpak_section.removed]
    )
    destructive += _flatpak_remove_commands(flatpak_section.added)

    ppa_section = sections_by_name["APT PPAs"]
    commands += apt_repo_restore(ppa_section.removed)
    destructive += _ppa_remove_commands(ppa_section.added)

    dotfile_section = sections_by_name["Dotfiles"]
    dotfiles_to_restore = dotfile_section.removed + dotfile_section.modified
    commands += _dotfile_restore_commands(source, dotfiles_to_restore)

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
