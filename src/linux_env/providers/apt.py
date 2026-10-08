from pathlib import Path
import re


def export_ppas() -> list[str]:
    """Return active Launchpad PPAs found in APT source files."""
    source_files = [Path("/etc/apt/sources.list")]
    source_dir = Path("/etc/apt/sources.list.d")

    if source_dir.exists():
        source_files.extend(
            sorted(
                p for p in source_dir.iterdir()
                if p.is_file() and p.suffix in {".list", ".sources"}
            )
        )

    ppas: set[str] = set()
    pattern = re.compile(r"ppa\.launchpadcontent\.net/([^/]+)/([^/]+)")

    for source_file in source_files:
        try:
            content = source_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        for line in content.splitlines():
            if line.lstrip().startswith("#"):
                continue
            match = pattern.search(line)
            if match:
                ppas.add(f"ppa:{match.group(1)}/{match.group(2)}")

    return sorted(ppas)


def restore_commands(ppas: list[str]) -> list[list[str]]:
    return [
        ["sudo", "add-apt-repository", "-y", ppa]
        for ppa in ppas
        if ppa.startswith("ppa:")
    ]
