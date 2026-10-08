from linux_env.manifest import load_manifest, save_manifest
from linux_env.models import EnvironmentManifest
from linux_env.providers.packages import restore_commands as package_restore
from linux_env.providers.snap import restore_commands as snap_restore


def test_manifest_roundtrip(tmp_path):
    path = tmp_path / "manifest.yaml"
    manifest = EnvironmentManifest(
        system={"distro": "ubuntu", "version": "24.04"},
        packages={"apt": ["git"]},
        snap=[{"name": "code", "channel": "latest/stable", "classic": True}],
        flatpaks=[{"app_id": "org.gnome.Calculator", "remote": "flathub"}],
        repositories={"apt_ppas": ["ppa:example/tool"]},
        dotfiles=[".bashrc"],
    )
    save_manifest(manifest, path)
    result = load_manifest(path)

    assert result.schema == 2
    assert result.system["distro"] == "ubuntu"
    assert result.packages["apt"] == ["git"]
    assert result.snap[0]["name"] == "code"
    assert result.flatpaks[0]["app_id"] == "org.gnome.Calculator"
    assert result.repositories["apt_ppas"] == ["ppa:example/tool"]


def test_apt_restore_commands():
    assert package_restore("apt", ["git"]) == [
        ["sudo", "apt-get", "update"],
        ["sudo", "apt-get", "install", "-y", "git"],
    ]


def test_snap_restore_commands():
    assert snap_restore(
        [{"name": "code", "channel": "latest/stable", "classic": True}]
    ) == [[
        "sudo", "snap", "install", "code",
        "--channel=latest/stable", "--classic"
    ]]
