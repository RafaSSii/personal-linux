from pathlib import Path
from .models import EnvironmentManifest
from .detect import detect
from .manifest import save_manifest, load_manifest
from .providers.packages import export_packages, restore_commands as package_restore
from .providers.flatpak import export_flatpaks, restore_commands as flatpak_restore
from .providers.dotfiles import backup as backup_dotfiles, restore_commands as dotfile_restore

def save_environment(destination: Path) -> EnvironmentManifest:
    destination.mkdir(parents=True, exist_ok=True)
    manager, packages = export_packages()
    manifest = EnvironmentManifest(system=detect(), packages={manager:packages} if manager else {}, flatpaks=export_flatpaks())
    manifest.dotfiles = backup_dotfiles(destination/"dotfiles")
    save_manifest(manifest, destination/"manifest.yaml")
    return manifest

def restore_environment(source: Path, dry_run: bool=False) -> list[list[str]]:
    manifest=load_manifest(source/"manifest.yaml"); commands=[]
    for manager,packages in manifest.packages.items(): commands += package_restore(manager,packages)
    commands += flatpak_restore(manifest.flatpaks)
    if manifest.dotfiles: commands += dotfile_restore()
    if not dry_run:
        import subprocess
        for command in commands: subprocess.run(command,check=True)
    return commands
