from pathlib import Path
import os
import platform
import shutil


def detect() -> dict:
    data = {
        "architecture": platform.machine(),
        "desktop": (
            os.environ.get("XDG_CURRENT_DESKTOP")
            or os.environ.get("DESKTOP_SESSION")
            or "unknown"
        ),
        "package_managers": [],
    }
    os_release = {}
    try:
        for line in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                os_release[key] = value.strip().strip('"')
    except OSError:
        pass

    distro = os_release.get("ID", "unknown").lower()
    data["distro"] = distro
    data["version"] = os_release.get("VERSION_ID", "unknown")
    data["id_like"] = os_release.get("ID_LIKE", "").lower().split()

    # Linux Mint shares Ubuntu's APT ecosystem only when Ubuntu-based.
    # LMDE is Debian-based and must not be treated as Ubuntu.
    if distro == "ubuntu":
        data["base_distro"] = "ubuntu"
        data["base_version"] = data["version"]
    elif distro == "linuxmint" and os_release.get("UBUNTU_CODENAME"):
        data["base_distro"] = "ubuntu"
        data["base_codename"] = os_release["UBUNTU_CODENAME"]

    for manager in ("apt-get", "dnf", "pacman", "zypper"):
        if shutil.which(manager):
            data["package_managers"].append(manager)
    data["flatpak"] = bool(shutil.which("flatpak"))
    data["snap"] = bool(shutil.which("snap"))
    return data


def distro_compatible(source: dict, target: dict) -> bool:
    """Whether a saved environment can safely cross between these distros."""
    source_distro = source.get("distro", "")
    target_distro = target.get("distro", "")

    if source_distro == target_distro:
        return True

    ubuntu_family = {"ubuntu", "linuxmint"}
    if source_distro not in ubuntu_family or target_distro not in ubuntu_family:
        return False

    def is_ubuntu_based(system: dict) -> bool:
        distro = system.get("distro")
        if distro == "ubuntu":
            return True
        return distro == "linuxmint" and system.get("base_distro") == "ubuntu"

    return is_ubuntu_based(source) and is_ubuntu_based(target)
