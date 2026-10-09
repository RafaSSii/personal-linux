from pathlib import Path
import subprocess

from linux_env.providers import apt, dotfiles, flatpak, snap


def test_export_ppas_reads_active_launchpad_sources(monkeypatch, tmp_path):
    source_list = tmp_path / "sources.list"
    source_dir = tmp_path / "sources.list.d"
    source_dir.mkdir()
    source_list.write_text(
        "# deb https://ppa.launchpad.net/ignored/ppa/ubuntu noble main\n"
        "deb https://ppa.launchpadcontent.net/alice/tools/ubuntu noble main\n",
        encoding="utf-8",
    )
    (source_dir / "extra.list").write_text(
        "deb https://ppa.launchpad.net/bob/apps/ubuntu noble main\n"
        "deb https://ppa.launchpad.net/alice/tools/ubuntu noble main\n",
        encoding="utf-8",
    )
    (source_dir / "disabled.list").write_text(
        "# deb https://ppa.launchpad.net/disabled/ppa/ubuntu noble main\n",
        encoding="utf-8",
    )
    real_path = Path

    def fake_path(value):
        if value == "/etc/apt/sources.list":
            return source_list
        if value == "/etc/apt/sources.list.d":
            return source_dir
        return real_path(value)

    monkeypatch.setattr(apt, "Path", fake_path)

    assert apt.export_ppas() == ["ppa:alice/tools", "ppa:bob/apps"]


def test_apt_restore_commands_ignores_invalid_entries():
    assert apt.restore_commands(["ppa:alice/tools", "not-a-ppa"]) == [
        ["sudo", "apt-get", "install", "-y", "software-properties-common"],
        ["sudo", "add-apt-repository", "-y", "ppa:alice/tools"],
    ]
    assert apt.restore_commands([]) == []


def test_export_snaps_preserves_channel_and_classic_and_ignores_base_snaps(
    monkeypatch,
):
    monkeypatch.setattr(snap.shutil, "which", lambda name: "/usr/bin/snap")
    monkeypatch.setattr(
        snap.subprocess,
        "check_output",
        lambda *args, **kwargs: (
            "Name  Version  Rev  Tracking       Publisher  Notes\n"
            "bare  1.0      5    latest/stable  canonical✓ -\n"
            "code  1.90     1    latest/stable  vscode✓    classic\n"
            "vlc   3.0      2    latest/stable  videolan✓  -\n"
        ),
    )

    assert snap.export_snaps() == [
        {"name": "code", "channel": "latest/stable", "classic": True},
        {"name": "vlc", "channel": "latest/stable"},
    ]


def test_export_snaps_returns_empty_when_snap_is_unavailable(monkeypatch):
    monkeypatch.setattr(snap.shutil, "which", lambda name: None)

    assert snap.export_snaps() == []


def test_snap_restore_commands_supports_current_and_legacy_manifest_entries():
    assert snap.restore_commands(
        [
            {"name": "code", "channel": "latest/stable", "classic": True},
            "vlc",
            {},
        ]
    ) == [
        [
            "sudo", "snap", "install", "code",
            "--channel=latest/stable", "--classic",
        ],
        ["sudo", "snap", "install", "vlc"],
    ]


def test_export_flatpaks_preserves_remotes_and_sorts_apps(monkeypatch):
    monkeypatch.setattr(flatpak.shutil, "which", lambda name: "/usr/bin/flatpak")
    monkeypatch.setattr(
        flatpak.subprocess,
        "check_output",
        lambda *args, **kwargs: (
            "org.mozilla.Firefox\tflathub\n"
            "org.gnome.Calculator\tflathub\n"
            "org.example.Local\t-\n"
        ),
    )

    assert flatpak.export_flatpaks() == [
        {"app_id": "org.example.Local"},
        {"app_id": "org.gnome.Calculator", "remote": "flathub"},
        {"app_id": "org.mozilla.Firefox", "remote": "flathub"},
    ]


def test_export_flatpaks_handles_missing_binary_and_command_failure(monkeypatch):
    monkeypatch.setattr(flatpak.shutil, "which", lambda name: None)
    assert flatpak.export_flatpaks() == []

    monkeypatch.setattr(flatpak.shutil, "which", lambda name: "/usr/bin/flatpak")

    def fail(*args, **kwargs):
        raise subprocess.CalledProcessError(1, ["flatpak"])

    monkeypatch.setattr(flatpak.subprocess, "check_output", fail)
    assert flatpak.export_flatpaks() == []


def test_flatpak_restore_commands_defaults_remote_and_supports_legacy_entries():
    assert flatpak.restore_commands(
        [
            {"app_id": "org.gnome.Calculator", "remote": "flathub"},
            {"app_id": "org.example.App"},
            "org.mozilla.Firefox",
            {},
        ]
    ) == [
        ["flatpak", "install", "-y", "flathub", "org.gnome.Calculator"],
        ["flatpak", "install", "-y", "flathub", "org.example.App"],
        ["flatpak", "install", "-y", "flathub", "org.mozilla.Firefox"],
    ]


def test_dotfiles_available_lists_only_existing_supported_files(monkeypatch, tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    (home / ".bashrc").write_text("export TEST=1\n", encoding="utf-8")
    (home / ".gitconfig").write_text("[user]\n", encoding="utf-8")
    monkeypatch.setattr(dotfiles.Path, "home", lambda: home)

    assert dotfiles.available() == [".bashrc", ".gitconfig"]


def test_dotfiles_backup_copies_content_and_creates_nested_directories(
    monkeypatch, tmp_path
):
    home = tmp_path / "home"
    (home / ".config/nvim").mkdir(parents=True)
    (home / ".config/nvim/init.lua").write_text("vim.opt.number = true\n")
    (home / ".zshrc").write_text("alias ll='ls -l'\n")
    destination = tmp_path / "backup"
    monkeypatch.setattr(dotfiles.Path, "home", lambda: home)

    copied = dotfiles.backup(destination)

    assert copied == [".zshrc", ".config/nvim/init.lua"]
    assert (destination / ".zshrc").read_text() == "alias ll='ls -l'\n"
    assert (
        destination / ".config/nvim/init.lua"
    ).read_text() == "vim.opt.number = true\n"


def test_dotfiles_restore_commands_only_returns_command_when_backup_exists(
    tmp_path,
):
    backup = tmp_path / "backup"
    assert dotfiles.restore_commands(backup) == []
    (backup / "dotfiles").mkdir(parents=True)
    assert dotfiles.restore_commands(backup) == [
        ["cp", "-a", f"{backup}/dotfiles/.", str(Path.home())]
    ]
