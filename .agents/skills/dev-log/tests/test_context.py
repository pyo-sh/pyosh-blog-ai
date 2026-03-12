from dev_log.context import detect_context


def test_detect_context_in_root(monorepo_root):
    result = detect_context(str(monorepo_root))
    assert result["inRootWorktree"] is False
    assert result["rootRepo"] == str(monorepo_root)
    assert result["worktreePath"] == ""


def test_detect_context_in_worktree(monorepo_root):
    wt = monorepo_root / ".workspace" / "worktrees" / "dev-log-test"
    wt.mkdir(parents=True)
    # .git file so git recognizes it (not a real repo, but context detection
    # only checks directory structure)
    result = detect_context(str(wt))
    assert result["inRootWorktree"] is True
    assert result["rootRepo"] == str(monorepo_root)
    assert result["worktreePath"] == str(wt)


def test_detect_context_nested_in_worktree(monorepo_root):
    wt = monorepo_root / ".workspace" / "worktrees" / "issue-42" / "docs"
    wt.mkdir(parents=True)
    result = detect_context(str(wt))
    assert result["inRootWorktree"] is True
    assert result["rootRepo"] == str(monorepo_root)


def test_detect_context_unknown_dir(tmp_path):
    result = detect_context(str(tmp_path))
    assert result["inRootWorktree"] is False
    assert result["rootRepo"] == str(tmp_path)
