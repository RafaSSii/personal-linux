"""Secure SSH transport for pulling a snapshot from another Linux host."""

from pathlib import Path, PurePosixPath
import subprocess
import tarfile
import tempfile

from .core import save_environment


def export_snapshot_stream(output) -> None:
    """Create a fresh snapshot and write a gzip tar archive to a binary stream."""
    with tempfile.TemporaryDirectory(prefix="linux-env-export-") as temporary:
        snapshot = Path(temporary) / "snapshot"
        save_environment(snapshot)
        with tarfile.open(fileobj=output, mode="w|gz") as archive:
            archive.add(snapshot, arcname="backup")


def _safe_extract(archive_path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path, mode="r:gz") as archive:
        members = archive.getmembers()
        if len(members) > 10000:
            raise RuntimeError("Remote snapshot contains too many entries.")
        total_size = sum(member.size for member in members if member.isfile())
        if total_size > 2 * 1024 * 1024 * 1024:
            raise RuntimeError("Remote snapshot exceeds the 2 GiB safety limit.")
        for member in members:
            name = PurePosixPath(member.name)
            if name.is_absolute() or ".." in name.parts:
                raise RuntimeError("Remote snapshot contains an unsafe path.")
            if not (member.isdir() or member.isfile()):
                raise RuntimeError("Remote snapshot contains an unsupported file type.")
            target = destination.joinpath(*name.parts)
            if target.resolve().parent != destination.resolve() and destination.resolve() not in target.resolve().parents:
                raise RuntimeError("Remote snapshot path escapes the destination.")
        archive.extractall(destination, members=members)


def pull_snapshot(remote: str, destination: Path, *, ssh_options: list[str] | None = None) -> Path:
    """Pull a snapshot over SSH without exposing a network listening service."""
    if not remote or remote.startswith("-") or any(char.isspace() for char in remote):
        raise ValueError("Remote must be in user@host form without whitespace.")
    ssh = ["ssh", *(ssh_options or []), remote, "linux-env", "export", "--stdout"]
    destination = destination.expanduser()
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError(f"Destination is not empty: {destination}")
    destination.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(prefix="linux-env-pull-", suffix=".tar.gz") as archive:
        result = subprocess.run(ssh, stdout=archive, check=False)
        if result.returncode:
            raise RuntimeError(
                f"SSH export failed with exit code {result.returncode}. "
                "Check SSH access and ensure linux-env is installed on the source."
            )
        archive.flush()
        _safe_extract(Path(archive.name), destination)

    snapshot = destination / "backup"
    if not (snapshot / "manifest.yaml").is_file():
        raise RuntimeError("The remote archive does not contain a valid linux-env manifest.")
    return snapshot
