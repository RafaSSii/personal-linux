from pathlib import Path

import pytest

from linux_env.core import apply_environment, plan_apply
from linux_env.diff import compare_sets


def _write_manifest(tmp_path: Path, packages: list[str], snap=None, flatpaks=None):
    (tmp_path / "manifest.yaml").write_text(
        f"""
schema: 2
system:
  distro: ubuntu
packages:
  apt:
{chr(10).join(f"    - {package}" for package in packages)}
snap: {snap or []}
flatpaks: {flatpaks or []}
repositories:
  apt_ppas: []
dotfiles: []
""",
        encoding="utf-8",
    )


def _mock_ubuntu(monkeypatch, packages):
    monkeypatch.setattr(
        "linux_env.core.detect",
        lambda: {"distro": "ubuntu"},
    )
    export_packages = lambda: ("apt-get", packages)
    monkeypatch.setattr("linux_env.core.export_packages", export_packages)
    monkeypatch.setattr("linux_env.diff.export_packages", export_packages)
    monkeypatch.setattr("linux_env.core.export_snaps", lambda: [])
    monkeypatch.setattr("linux_env.core.export_flatpaks", lambda: [])
    monkeypatch.setattr("linux_env.core.export_ppas", lambda: [])


def test_compare_sets_reports_added_and_removed():
    result = compare_sets(
        "APT packages",
        {"git", "curl"},
        {"git", "neovim"},
    )

    assert result.added == ["neovim"]
    assert result.removed == ["curl"]
    assert result.changed is True


def test_compare_sets_reports_sync():
    result = compare_sets("Snap", {"code"}, {"code"})

    assert result.changed is False


def test_apply_plan_installs_missing_packages(monkeypatch, tmp_path):
    _write_manifest(tmp_path, ["git", "curl"])
    _mock_ubuntu(monkeypatch, ["git"])

    commands, destructive = plan_apply(tmp_path)

    assert commands == [
        ["sudo", "apt-get", "update"],
        ["sudo", "apt-get", "install", "-y", "curl"],
    ]
    assert destructive == []


def test_apply_plan_marks_package_removal_destructive(monkeypatch, tmp_path):
    _write_manifest(tmp_path, ["git"])
    _mock_ubuntu(monkeypatch, ["git", "vlc"])

    commands, destructive = plan_apply(tmp_path)

    assert commands == []
    assert destructive == [["sudo", "apt-get", "remove", "-y", "vlc"]]


def test_apply_requires_confirmation_for_destructive_changes(monkeypatch, tmp_path):
    _write_manifest(tmp_path, ["git"])
    _mock_ubuntu(monkeypatch, ["git", "vlc"])

    with pytest.raises(RuntimeError, match="destructive changes"):
        apply_environment(tmp_path)


def test_apply_executes_after_confirmation(monkeypatch, tmp_path):
    _write_manifest(tmp_path, ["git", "curl"])
    _mock_ubuntu(monkeypatch, ["git"])

    executed = []
    class SubprocessStub:
        @staticmethod
        def run(command, check):
            executed.append(command)

    monkeypatch.setattr("linux_env.core.subprocess", SubprocessStub)

    result = apply_environment(
        tmp_path,
        confirm=lambda: True,
    )

    assert result == [
        ["sudo", "apt-get", "update"],
        ["sudo", "apt-get", "install", "-y", "curl"],
    ]
    assert executed == result


def test_dry_run_never_executes(monkeypatch, tmp_path):
    _write_manifest(tmp_path, ["git"])
    _mock_ubuntu(monkeypatch, ["git", "vlc"])

    executed = []
    monkeypatch.setattr(
        "linux_env.core.subprocess.run",
        lambda command, check: executed.append(command),
    )

    result = apply_environment(tmp_path, dry_run=True)

    assert result == [["sudo", "apt-get", "remove", "-y", "vlc"]]
    assert executed == []


def test_assume_yes_allows_destructive_changes(monkeypatch, tmp_path):
    _write_manifest(tmp_path, ["git"])
    _mock_ubuntu(monkeypatch, ["git", "vlc"])

    executed = []
    monkeypatch.setattr(
        "linux_env.core.subprocess.run",
        lambda command, check: executed.append(command),
    )

    apply_environment(tmp_path, assume_yes=True)

    assert executed == [["sudo", "apt-get", "remove", "-y", "vlc"]]


def test_apply_preserves_snap_metadata(monkeypatch, tmp_path):
    _write_manifest(
        tmp_path,
        ["git"],
        snap=[{"name": "code", "channel": "latest/stable", "classic": True}],
    )
    _mock_ubuntu(monkeypatch, ["git"])
    monkeypatch.setattr("linux_env.core.export_snaps", lambda: [])

    commands, destructive = plan_apply(tmp_path)

    assert commands == [[
        "sudo", "snap", "install", "code",
        "--channel=latest/stable", "--classic",
    ]]
    assert destructive == []
