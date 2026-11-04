import io
import tarfile
from pathlib import Path
import subprocess

import pytest

from linux_env.transfer import _safe_extract, pull_snapshot


def test_safe_extract_rejects_path_traversal(tmp_path):
    archive_path = tmp_path / "bad.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        info = tarfile.TarInfo("../escape")
        info.size = 4
        archive.addfile(info, io.BytesIO(b"oops"))

    with pytest.raises(RuntimeError, match="unsafe path"):
        _safe_extract(archive_path, tmp_path / "out")


def test_safe_extract_rejects_links(tmp_path):
    archive_path = tmp_path / "link.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        info = tarfile.TarInfo("backup/link")
        info.type = tarfile.SYMTYPE
        info.linkname = "/etc/passwd"
        archive.addfile(info)

    with pytest.raises(RuntimeError, match="unsupported file type"):
        _safe_extract(archive_path, tmp_path / "out")


def test_pull_uses_ssh_and_returns_snapshot(tmp_path, monkeypatch):
    def fake_run(command, stdout, check):
        assert command == ["ssh", "rafael@192.168.1.10", "linux-env", "export", "--stdout"]
        with tarfile.open(fileobj=stdout, mode="w:gz") as archive:
            payload = b"schema: 2\nsystem: {}\n"
            info = tarfile.TarInfo("backup/manifest.yaml")
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = pull_snapshot("rafael@192.168.1.10", tmp_path / "received")

    assert result == tmp_path / "received" / "backup"
    assert (result / "manifest.yaml").read_text() == "schema: 2\nsystem: {}\n"


def test_pull_refuses_nonempty_destination(tmp_path):
    destination = tmp_path / "existing"
    destination.mkdir()
    (destination / "keep").write_text("data")

    with pytest.raises(FileExistsError):
        pull_snapshot("rafael@example.com", destination)


def test_pull_rejects_invalid_remote(tmp_path):
    with pytest.raises(ValueError):
        pull_snapshot("-oProxyCommand=bad", tmp_path / "out")
