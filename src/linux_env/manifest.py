from pathlib import Path

import yaml

from .models import EnvironmentManifest


def save_manifest(manifest: EnvironmentManifest, path: Path) -> None:
    data = {
        "schema": manifest.schema,
        "system": manifest.system,
        "packages": manifest.packages,
        "snap": manifest.snap,
        "flatpaks": manifest.flatpaks,
        "repositories": manifest.repositories,
        "dotfiles": manifest.dotfiles,
    }
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def load_manifest(path: Path) -> EnvironmentManifest:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return EnvironmentManifest(
        schema=data.get("schema", 1),
        system=data.get("system", {}),
        packages=data.get("packages", {}),
        snap=data.get("snap", []),
        flatpaks=data.get("flatpaks", []),
        repositories=data.get("repositories", {}),
        dotfiles=data.get("dotfiles", []),
    )
