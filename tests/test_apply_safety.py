from pathlib import Path
import subprocess

import pytest

from linux_env import core
from linux_env.diff import DiffSection
from linux_env.providers import dotfiles


def _manifest(tmp_path, *, distro="ubuntu", packages=None, dotfile_paths=None):
    (tmp_path / "manifest.yaml").write_text(
        "schema: 2\n"
        f"system:\n  distro: {distro}\n"
        "packages:\n  apt:\n"
        + "".join(f"    - {p}\n" for p in (packages or []))
        + "snap: []\nflatpaks: []\nrepositories:\n  apt_ppas: []\n"
        + "dotfiles:\n"
        + "".join(f"  - {p}\n" for p in (dotfile_paths or [])),
        encoding="utf-8",
    )


def _mock_diff(monkeypatch, sections):
    monkeypatch.setattr(core, "detect", lambda: {"distro": "ubuntu"})
    monkeypatch.setattr(core, "export_packages", lambda: ("apt-get", []))
    monkeypatch.setattr(core, "compare_manifest_to_system", lambda source: (
        {"system": {}, "source": str(source)}, sections
    ))
    monkeypatch.setattr(core, "apt_repo_restore", lambda values: [])
    monkeypatch.setattr(core, "package_restore", lambda manager, values: [])
    monkeypatch.setattr(core, "snap_restore", lambda values: [])
    monkeypatch.setattr(core, "flatpak_restore", lambda values: [])


def test_apply_declining_confirmation_never_executes_commands(monkeypatch, tmp_path):
    _manifest(tmp_path)
    _mock_diff(monkeypatch, [
        DiffSection("APT packages", ["vlc"], [], []),
        DiffSection("Snap", [], [], []),
        DiffSection("Flatpak", [], [], []),
        DiffSection("APT PPAs", [], [], []),
        DiffSection("Dotfiles", [], [], []),
    ])
    executed = []
    monkeypatch.setattr(core, "subprocess", type("SubprocessStub", (), {
        "run": staticmethod(lambda command, check: executed.append(command))
    }))

    with pytest.raises(RuntimeError, match="cancelled"):
        core.apply_environment(tmp_path, confirm=lambda: False)

    assert executed == []


def test_apply_stops_after_first_command_failure(monkeypatch, tmp_path):
    _manifest(tmp_path, packages=["git", "curl"])
    _mock_diff(monkeypatch, [
        DiffSection("APT packages", [], ["git", "curl"], []),
        DiffSection("Snap", [], [], []),
        DiffSection("Flatpak", [], [], []),
        DiffSection("APT PPAs", [], [], []),
        DiffSection("Dotfiles", [], [], []),
    ])
    monkeypatch.setattr(core, "package_restore", lambda manager, values: [["install", *values]])
    calls = []

    def fail_first(command, check):
        calls.append(command)
        raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(core, "subprocess", type("SubprocessStub", (), {
        "run": staticmethod(fail_first)
    }))

    with pytest.raises(subprocess.CalledProcessError):
        core.apply_environment(tmp_path)

    assert len(calls) == 1


def test_apply_rejects_ubuntu_manifest_on_non_ubuntu(monkeypatch, tmp_path):
    _manifest(tmp_path, distro="ubuntu")
    monkeypatch.setattr(core, "detect", lambda: {"distro": "fedora"})

    with pytest.raises(RuntimeError, match="not currently considered compatible"):
        core.plan_apply(tmp_path)


def test_apply_rejects_malformed_manifest_without_running_commands(monkeypatch, tmp_path):
    (tmp_path / "manifest.yaml").write_text("not: [valid", encoding="utf-8")
    executed = []
    monkeypatch.setattr(core, "subprocess", type("SubprocessStub", (), {
        "run": staticmethod(lambda command, check: executed.append(command))
    }))

    with pytest.raises(Exception):
        core.apply_environment(tmp_path, assume_yes=True)

    assert executed == []


def test_dotfiles_backup_never_copies_files_outside_allowlist(monkeypatch, tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    (home / ".bashrc").write_text("safe config", encoding="utf-8")
    (home / ".ssh").mkdir()
    (home / ".ssh/id_ed25519").write_text("PRIVATE KEY", encoding="utf-8")
    (home / ".gnupg").mkdir()
    (home / ".gnupg/private-key").write_text("PRIVATE KEY", encoding="utf-8")
    monkeypatch.setattr(dotfiles.Path, "home", lambda: home)
    destination = tmp_path / "backup"

    copied = dotfiles.backup(destination)

    assert copied == [".bashrc"]
    assert (destination / ".bashrc").read_text(encoding="utf-8") == "safe config"
    assert not (destination / ".ssh").exists()
    assert not (destination / ".gnupg").exists()


def test_dotfiles_backup_handles_empty_home(monkeypatch, tmp_path):
    home = tmp_path / "empty-home"
    home.mkdir()
    monkeypatch.setattr(dotfiles.Path, "home", lambda: home)

    assert dotfiles.backup(tmp_path / "backup") == []
