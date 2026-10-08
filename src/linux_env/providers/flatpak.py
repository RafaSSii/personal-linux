import shutil, subprocess

def export_flatpaks() -> list[str]:
    if not shutil.which("flatpak"): return []
    try: out = subprocess.check_output(["flatpak","list","--app","--columns=application"], text=True, stderr=subprocess.DEVNULL)
    except (OSError, subprocess.CalledProcessError): return []
    return sorted({x.strip() for x in out.splitlines() if x.strip() and x.strip() != "Application"})

def restore_commands(apps: list[str]) -> list[list[str]]:
    return [["flatpak","install","-y","flathub",*apps]] if apps else []
