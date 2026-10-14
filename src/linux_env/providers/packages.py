import re
import shutil
import subprocess

# These packages are tied to boot, kernel, hardware, or the source distro.
# They are intentionally excluded from automatic cross-installation.
BOOT_EXACT = {
    "base", "grub", "grub-btrfs", "install-grub", "update-grub",
    "efibootmgr", "os-prober", "mkinitcpio", "mkinitcpio-openswap",
    "systemd-boot", "shim", "sbctl",
}
BOOT_PREFIXES = ("grub-theme-", "kernel-", "initramfs-")
HARDWARE_EXACT = {"amd-ucode", "intel-ucode", "alsa-firmware", "linux-firmware"}
HARDWARE_PREFIXES = (
    "xf86-video-", "xf86-input-", "nvidia", "virtualbox-host",
    "lib32-vulkan-", "vulkan-", "lib32-mesa", "mesa",
)
DISTRO_PREFIXES = ("manjaro-",)


def classify_package(name: str) -> str:
    """Return a conservative restore category for a package name."""
    normalized = name.strip().lower()
    if (
        normalized in BOOT_EXACT
        or re.match(r"linux(?:[0-9]|-(?:lts|zen|hardened|rt|image|headers))", normalized)
        or any(normalized.startswith(prefix) for prefix in BOOT_PREFIXES)
    ):
        return "boot"
    if (
        normalized in HARDWARE_EXACT
        or any(normalized.startswith(prefix) for prefix in HARDWARE_PREFIXES)
        or normalized in {"mhwd", "mhwd-db", "cpupower"}
    ):
        return "hardware"
    if any(normalized.startswith(prefix) for prefix in DISTRO_PREFIXES):
        return "distribution"
    if normalized in {"base-devel", "build-essential", "gcc", "make", "git"}:
        return "development"
    return "application"


def safe_restore_packages(packages: list[str]) -> tuple[list[str], dict[str, list[str]]]:
    """Keep portable packages and report packages skipped for safety."""
    selected = []
    skipped: dict[str, list[str]] = {}
    for package in sorted(set(packages)):
        category = classify_package(package)
        if category in {"boot", "hardware", "distribution"}:
            skipped.setdefault(category, []).append(package)
        else:
            selected.append(package)
    return selected, skipped


def installed_packages(manager: str) -> set[str]:
    """Read installed package names using the selected system package manager."""
    commands = {
        "apt-get": ["dpkg-query", "-W", "-f=${binary:Package}\\n"],
        "dnf": ["rpm", "-qa", "--qf", "%{NAME}\\n"],
        "pacman": ["pacman", "-Qq"],
        "zypper": ["rpm", "-qa", "--qf", "%{NAME}\\n"],
    }
    command = commands.get(manager)
    if not command:
        return set()
    try:
        output = subprocess.check_output(
            command, text=True, stderr=subprocess.DEVNULL
        )
    except (OSError, subprocess.CalledProcessError):
        return set()
    return {line.strip().split(":")[0] for line in output.splitlines() if line.strip()}


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
        output = _run(["apt-mark", "showmanual"])
    elif manager == "dnf":
        output = _run(["dnf", "repoquery", "--userinstalled", "--qf", "%{name}"])
        if not output:
            output = _run(["rpm", "-qa", "--qf", "%{NAME}\\n"])
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
