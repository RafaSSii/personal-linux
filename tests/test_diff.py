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
