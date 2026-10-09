"""Black-box integration tests for the installed CLI using isolated fake system tools."""

import os
from pathlib import Path
import subprocess
import sys

import yaml


REPO = "RafaSSii/personal-linux"


def _fake_tools(tmp_path: Path, monkeypatch, outputs: dict[str, str] | None = None) -> Path:
    bin_dir = tmp_path / "fake-bin"
    bin_dir.mkdir()
    log = tmp_path / "commands.log"
    monkeypatch.setenv("LINUX_ENV_TEST_LOG", str(log))

    scripts = {
        "apt-get": "",
        "apt-mark": "printf 'git\\ncurl\\n'\n",
        "sudo": "",
        "snap": "if [ \"$1\" = list ]; then printf 'Name Version Rev Tracking Publisher Notes\\ncode 1 123 latest/stable vendor classic\\n' ; fi\n",
        "flatpak": "if [ \"$1\" = list ]; then printf 'org.example.Editor\\tflathub\\n' ; fi\n",
        "cp": "",
        "add-apt-repository": "",
    }
    scripts.update(outputs or {})
    for name, body in scripts.items():
        executable = bin_dir / name
        executable.write_text(
            "#!/bin/sh\n"
            'printf "%s %s\\n" "$(basename "$0")" "$*" >> "$LINUX_ENV_TEST_LOG"\n'
            + body
            + "\n",
            encoding="utf-8",
        )
        executable.chmod(0o755)

    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    return log


def _run_cli(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "linux_env.cli", *args],
        text=True,
        capture_output=True,
        env=env or os.environ.copy(),
        check=False,
    )


def test_save_cli_exports_environment_into_manifest_and_dotfiles(tmp_path, monkeypatch):
    _fake_tools(tmp_path, monkeypatch)
    home = tmp_path / "home"
    home.mkdir()
    (home / ".bashrc").write_text("export SAMPLE=1\n", encoding="utf-8")
    (home / ".gitconfig").write_text("[user]\n  name = Example\n", encoding="utf-8")
    monkeypatch.setenv("HOME", str(home))

    destination = tmp_path / "snapshot"
    result = _run_cli("save", str(destination))

    assert result.returncode == 0, result.stderr
    assert "Environment saved" in result.stdout
    manifest = yaml.safe_load((destination / "manifest.yaml").read_text(encoding="utf-8"))
    assert manifest["schema"] == 2
    assert manifest["packages"]["apt"] == ["curl", "git"]
    assert manifest["snap"] == [{"name": "code", "channel": "latest/stable", "classic": True}]
    assert manifest["flatpaks"] == [{"app_id": "org.example.Editor", "remote": "flathub"}]
    assert sorted(manifest["dotfiles"]) == [".bashrc", ".gitconfig"]
    assert (destination / "dotfiles" / ".bashrc").read_text(encoding="utf-8") == "export SAMPLE=1\n"


def test_restore_cli_executes_only_planned_commands_through_fake_path(tmp_path, monkeypatch):
    log = _fake_tools(tmp_path, monkeypatch)
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))

    snapshot = tmp_path / "snapshot"
    dotfiles = snapshot / "dotfiles"
    dotfiles.mkdir(parents=True)
    (dotfiles / ".bashrc").write_text("export RESTORED=1\n", encoding="utf-8")
    manifest = {
        "schema": 2,
        "system": {},
        "packages": {"apt": ["git"]},
        "snap": [{"name": "code", "channel": "latest/stable", "classic": True}],
        "flatpaks": [{"app_id": "org.example.Editor", "remote": "flathub"}],
        "repositories": {},
        "dotfiles": [".bashrc"],
    }
    (snapshot / "manifest.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")

    result = _run_cli("restore", str(snapshot))

    assert result.returncode == 0, result.stderr
    assert "sudo apt-get update" in result.stdout
    assert "sudo snap install code --channel=latest/stable --classic" in result.stdout
    assert "flatpak install -y flathub org.example.Editor" in result.stdout
    executed = log.read_text(encoding="utf-8").splitlines()
    assert "sudo apt-get update" in executed
    assert "sudo apt-get install -y git" in executed
    assert "sudo snap install code --channel=latest/stable --classic" in executed
    assert "flatpak install -y flathub org.example.Editor" in executed
    assert any(line.startswith("cp -a ") for line in executed)


def test_restore_dry_run_prints_plan_without_executing_commands(tmp_path, monkeypatch):
    log = _fake_tools(tmp_path, monkeypatch)
    snapshot = tmp_path / "snapshot"
    snapshot.mkdir()
    (snapshot / "manifest.yaml").write_text(
        yaml.safe_dump({
            "schema": 2,
            "system": {},
            "packages": {"apt": ["git"]},
            "snap": [],
            "flatpaks": [],
            "repositories": {},
            "dotfiles": [],
        }),
        encoding="utf-8",
    )

    result = _run_cli("restore", str(snapshot), "--dry-run")

    assert result.returncode == 0, result.stderr
    assert "sudo apt-get update" in result.stdout
    assert "sudo apt-get install -y git" in result.stdout
    assert not log.exists() or log.read_text(encoding="utf-8") == ""
