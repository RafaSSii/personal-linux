import shutil
import subprocess


def detect_manager() -> str | None:
    for manager in ("apt-get", "dnf", "pacman", "zypper"):
        if shutil.which(manager):
            return manager
    return None


def _run(command: list[str]) -> str:
    try:
        return subprocess.check_output(
            command, text=True, stderr=subprocess.DEVNULL
        )
    except (OSError, subprocess.CalledProcessError):
        return ""


def export_packages() -> tuple[str | None, list[str]]:
    manager = detect_manager()
    if not manager:
        return None, []

    if manager == "apt-get":
        # apt-mark showmanual is preferable to dpkg-query here: it excludes
        # packages installed only as dependencies.
        output = _run(["apt-mark", "showmanual"])
    elif manager == "dnf":
        output = _run(["dnf", "repoquery", "--userinstalled", "--qf", "%{name}"])
        if not output:
            output = _run(["rpm", "-qa", "--qf", "%{NAME}\n"])
    elif manager == "pacman":
        output = _run(["pacman", "-Qqe"])
    else:
        output = _run(["zypper", "packages", "--userinstalled"])

    packages = sorted(
        {line.strip() for line in output.splitlines() if line.strip()}
    )
    return manager, packages


def restore_commands(manager: str, packages: list[str]) -> list[list[str]]:
    if not packages:
        return []

    if manager in ("apt", "apt-get"):
        return [
            ["sudo", "apt-get", "update"],
            ["sudo", "apt-get", "install", "-y", *packages],
        ]
    if manager == "dnf":
        return [["sudo", "dnf", "install", "-y", *packages]]
    if manager == "pacman":
        return [["sudo", "pacman", "-S", "--needed", *packages]]
    if manager == "zypper":
        return [["sudo", "zypper", "install", "-y", *packages]]
    return []
