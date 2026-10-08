from pathlib import Path
import os, platform, shutil

def detect() -> dict:
    data = {"architecture": platform.machine(), "desktop": os.environ.get("XDG_CURRENT_DESKTOP") or os.environ.get("DESKTOP_SESSION") or "unknown", "package_managers": []}
    os_release = {}
    try:
        for line in Path("/etc/os-release").read_text().splitlines():
            if "=" in line:
                k, v = line.split("=", 1); os_release[k] = v.strip('"')
    except OSError: pass
    data["distro"] = os_release.get("ID", "unknown")
    data["version"] = os_release.get("VERSION_ID", "unknown")
    for manager in ("apt-get", "dnf", "pacman", "zypper"):
        if shutil.which(manager): data["package_managers"].append(manager)
    data["flatpak"] = bool(shutil.which("flatpak"))
    return data
