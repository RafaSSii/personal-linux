from pathlib import Path
import yaml
from .models import EnvironmentManifest

def save_manifest(manifest: EnvironmentManifest, path: Path) -> None:
    path.write_text(yaml.safe_dump({"schema": manifest.schema, "system": manifest.system, "packages": manifest.packages, "dotfiles": manifest.dotfiles, "flatpaks": manifest.flatpaks}, sort_keys=False), encoding="utf-8")

def load_manifest(path: Path) -> EnvironmentManifest:
    d = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return EnvironmentManifest(schema=d.get("schema", 1), system=d.get("system", {}), packages=d.get("packages", {}), dotfiles=d.get("dotfiles", []), flatpaks=d.get("flatpaks", []))
