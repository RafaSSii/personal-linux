from pathlib import Path
FILES = [".bashrc",".zshrc",".gitconfig",".config/nvim/init.lua"]

def available() -> list[str]:
    home = Path.home()
    return [p for p in FILES if (home / p).exists()]

def backup(destination: Path) -> list[str]:
    home = Path.home(); copied=[]
    for rel in available():
        src,dst=home/rel,destination/rel
        dst.parent.mkdir(parents=True,exist_ok=True); dst.write_bytes(src.read_bytes()); copied.append(rel)
    return copied

def restore_commands() -> list[list[str]]:
    return [["cp","-a","dotfiles/.",str(Path.home())]]
