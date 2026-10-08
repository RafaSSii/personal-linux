from linux_env.core import plan_apply
from linux_env.diff import compare_sets


def test_compare_sets_reports_added_and_removed():
    result = compare_sets(
        "APT packages",
        {"git", "curl"},
        {"git", "neovim"},
    )

    assert result.name == "APT packages"
    assert result.added == ["neovim"]
    assert result.removed == ["curl"]
    assert result.changed is True


def test_compare_sets_reports_sync():
    result = compare_sets("Snap", {"code"}, {"code"})

    assert result.added == []
    assert result.removed == []
    assert result.changed is False


def test_apply_plan_marks_removals_as_destructive(monkeypatch, tmp_path):
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        """
schema: 2
system:
  distro: ubuntu
packages:
  apt:
    - git
snap: []
flatpaks: []
repositories:
  apt_ppas: []
dotfiles: []
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "linux_env.core.detect",
        lambda: {"distro": "ubuntu"},
    )
    monkeypatch.setattr(
        "linux_env.core.export_packages",
        lambda: ("apt-get", ["git", "vlc"]),
    )
    monkeypatch.setattr("linux_env.core.export_snaps", lambda: [])
    monkeypatch.setattr("linux_env.core.export_flatpaks", lambda: [])
    monkeypatch.setattr("linux_env.core.export_ppas", lambda: [])

    commands, destructive = plan_apply(tmp_path)

    assert commands == []
    assert destructive == [["sudo", "apt-get", "remove", "-y", "vlc"]]


def test_apply_plan_installs_missing_packages(monkeypatch, tmp_path):
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text(
        """
schema: 2
system:
  distro: ubuntu
packages:
  apt:
    - git
    - curl
snap: []
flatpaks: []
repositories:
  apt_ppas: []
dotfiles: []
""",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "linux_env.core.detect",
        lambda: {"distro": "ubuntu"},
    )
    monkeypatch.setattr(
        "linux_env.core.export_packages",
        lambda: ("apt-get", ["git"]),
    )
    monkeypatch.setattr("linux_env.core.export_snaps", lambda: [])
    monkeypatch.setattr("linux_env.core.export_flatpaks", lambda: [])
    monkeypatch.setattr("linux_env.core.export_ppas", lambda: [])

    commands, destructive = plan_apply(tmp_path)

    assert commands == [
        ["sudo", "apt-get", "update"],
        ["sudo", "apt-get", "install", "-y", "curl"],
    ]
    assert destructive == []
