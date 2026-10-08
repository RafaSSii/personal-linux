from pathlib import Path

FILES = [".bashrc", ".zshrc", ".gitconfig", ".config/nvim/init.lua"]


def available() -> list[str]:
    home = Path.home()
    return [path for path in FILES if (home / path).exists()]


def backup(destination: Path) -> list[str]:
    home = Path.home()
    copied = []
    for relative in available():
        source, target = home / relative, destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
        copied.append(relative)
    return copied


def restore_commands(source: Path) -> list[list[str]]:
    dotfiles = source / "dotfiles"
    return [["cp", "-a", f"{dotfiles}/.", str(Path.home())]] if dotfiles.exists() else []
