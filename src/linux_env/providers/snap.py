import shutil
import subprocess
from typing import Any


BASE_SNAPS = {
    "bare", "core", "core18", "core20", "core22", "core24", "snapd"
}


def export_snaps() -> list[dict[str, Any]]:
    if not shutil.which("snap"):
        return []

    try:
        output = subprocess.check_output(
            ["snap", "list"], text=True, stderr=subprocess.DEVNULL
        )
    except (OSError, subprocess.CalledProcessError):
        return []

    snaps: list[dict[str, Any]] = []
    for line in output.splitlines()[1:]:
        parts = line.split()
        if not parts or parts[0] in BASE_SNAPS:
            continue

        name = parts[0]
        tracking = parts[3] if len(parts) > 3 else ""
        notes = " ".join(parts[5:]) if len(parts) > 5 else ""

        item: dict[str, Any] = {"name": name}
        if tracking and tracking != "-":
            item["channel"] = tracking
        if "classic" in notes.split():
            item["classic"] = True
        snaps.append(item)

    return sorted(snaps, key=lambda item: item["name"])


def restore_commands(snaps: list[dict[str, Any] | str]) -> list[list[str]]:
    commands: list[list[str]] = []

    for item in snaps:
        if isinstance(item, str):
            name, channel, classic = item, None, False
        else:
            name = item.get("name")
            channel = item.get("channel")
            classic = bool(item.get("classic"))

        if not name:
            continue

        command = ["sudo", "snap", "install", name]
        if channel:
            command.append(f"--channel={channel}")
        if classic:
            command.append("--classic")
        commands.append(command)

    return commands
