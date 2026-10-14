from datetime import datetime
from pathlib import Path

FILES = [".bashrc", ".zshrc", ".gitconfig", ".config/nvim/init.lua"]


def available() -> list[str]:
    home = Path.home()
    return [path for path in FILES if (home / path).is_file()]


def backup(destination: Path) -> list[str]:
    home = Path.home()
    copied = []
    for relative in available():
        source, target = home / relative, destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
        copied.append(relative)
    return copied


def restore_plan(
    source: Path,
    *,
    home: Path | None = None,
    backup_root: Path | None = None,
) -> tuple[list[list[str]], list[str]]:
    """Build per-file restore commands and report existing files that will be backed up."""
    home = home or Path.home()
    dotfiles = source / "dotfiles"
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup_root = backup_root or (
        home / ".local/share/linux-env/restore-backups" / stamp
    )
    commands: list[list[str]] = []
    conflicts: list[str] = []

    for relative in FILES:
        saved = dotfiles / relative
        if not saved.is_file() or saved.is_symlink():
            continue
        target = home / relative
        commands.append(["mkdir", "-p", str(target.parent)])
        if target.exists() or target.is_symlink():
            conflicts.append(relative)
            backup_target = backup_root / relative
            commands.append(["mkdir", "-p", str(backup_target.parent)])
            commands.append(["cp", "-a", str(target), str(backup_target)])
        commands.append(["cp", "-a", str(saved), str(target)])
    return commands, conflicts


def restore_commands(source: Path) -> list[list[str]]:
    commands, _ = restore_plan(source)
    return commands
