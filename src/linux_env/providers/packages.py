import subprocess, shutil

def detect_manager() -> str | None:
    for m in ("apt-get", "dnf", "pacman", "zypper"):
        if shutil.which(m): return m
    return None

def export_packages() -> tuple[str | None, list[str]]:
    m = detect_manager()
    if not m: return None, []
    commands = {"apt-get":["dpkg-query","-W","-f=${binary:Package}\\n"],"dnf":["rpm","-qa","--qf","%{NAME}\\n"],"pacman":["pacman","-Qq"],"zypper":["rpm","-qa","--qf","%{NAME}\\n"]}
    try: out = subprocess.check_output(commands[m], text=True, stderr=subprocess.DEVNULL)
    except (OSError, subprocess.CalledProcessError): return m, []
    return m, sorted({x.strip() for x in out.splitlines() if x.strip()})

def restore_commands(manager: str, packages: list[str]) -> list[list[str]]:
    if not packages: return []
    if manager == "apt-get": return [["sudo","apt-get","install","-y",*packages]]
    if manager == "dnf": return [["sudo","dnf","install","-y",*packages]]
    if manager == "pacman": return [["sudo","pacman","-S","--needed",*packages]]
    if manager == "zypper": return [["sudo","zypper","install","-y",*packages]]
    return []
