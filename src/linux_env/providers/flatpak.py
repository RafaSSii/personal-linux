import shutil
import subprocess
from typing import Any


def export_flatpaks() -> list[dict[str, Any]]:
    if not shutil.which("flatpak"):
        return []

    try:
        output = subprocess.check_output(
            ["flatpak", "list", "--app", "--columns=application,origin"],
            text=True, stderr=subprocess.DEVNULL
        )
    except (OSError, subprocess.CalledProcessError):
        return []

    apps = []
    for line in output.splitlines():
        parts = line.split("\t", 1)
        app_id = parts[0].strip()
        remote = parts[1].strip() if len(parts) > 1 else ""
        if not app_id or app_id == "Application":
            continue
        item: dict[str, Any] = {"app_id": app_id}
        if remote and remote != "-":
            item["remote"] = remote
        apps.append(item)
    return sorted(apps, key=lambda item: item["app_id"])


def restore_commands(apps: list[Any]) -> list[list[str]]:
    commands = []
    for item in apps:
        if isinstance(item, str):
            app_id, remote = item, "flathub"
        else:
            app_id, remote = item.get("app_id"), item.get("remote") or "flathub"
        if app_id:
            commands.append(["flatpak", "install", "-y", remote, app_id])
    return commands
