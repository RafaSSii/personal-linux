from pathlib import Path

from .detect import detect
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
    for manager, packages in manifest.packages.items():
        commands += _restore_package_manager(manager, packages)

    commands += apt_repo_restore(manifest.repositories.get("apt_ppas", []))
    commands += snap_restore(manifest.snap)
    commands += flatpak_restore(manifest.flatpaks)

    if manifest.dotfiles:
        commands += dotfile_restore(source)

    if not dry_run:
        import subprocess
        for command in commands:
            subprocess.run(command, check=True)

    return commands
