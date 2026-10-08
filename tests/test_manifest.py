from linux_env.manifest import load_manifest, save_manifest
from linux_env.models import EnvironmentManifest

def test_manifest_roundtrip(tmp_path):
    path=tmp_path/"manifest.yaml"
    manifest=EnvironmentManifest(system={"distro":"test"},packages={"apt-get":["git"]},flatpaks=["org.gnome.Calculator"],dotfiles=[".bashrc"])
    save_manifest(manifest,path); result=load_manifest(path)
    assert result.system["distro"]=="test"
    assert result.packages["apt-get"]==["git"]
    assert result.flatpaks==["org.gnome.Calculator"]
