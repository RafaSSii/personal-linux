from linux_env.detect import distro_compatible


def test_ubuntu_manifest_is_compatible_with_ubuntu_based_mint():
    assert distro_compatible(
        {"distro": "ubuntu"},
        {"distro": "linuxmint", "base_distro": "ubuntu", "base_codename": "noble"},
    )


def test_ubuntu_based_mint_manifest_is_compatible_with_ubuntu():
    assert distro_compatible(
        {"distro": "linuxmint", "base_distro": "ubuntu", "base_codename": "noble"},
        {"distro": "ubuntu", "base_distro": "ubuntu"},
    )


def test_lmde_is_not_treated_as_ubuntu_compatible():
    assert not distro_compatible(
        {"distro": "linuxmint", "base_distro": "debian"},
        {"distro": "ubuntu", "base_distro": "ubuntu"},
    )


def test_unrelated_distributions_remain_incompatible():
    assert not distro_compatible(
        {"distro": "ubuntu"},
        {"distro": "fedora"},
    )


def test_same_distribution_is_compatible():
    assert distro_compatible(
        {"distro": "linuxmint"},
        {"distro": "linuxmint"},
    )
