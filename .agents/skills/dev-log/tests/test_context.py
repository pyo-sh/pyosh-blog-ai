from dev_log.context import detect_context


def _make_root_worktree(monorepo_root, name):
    """Create a worktree directory with a .git file pointing to root repo."""
    wt = monorepo_root / ".workspace" / "worktrees" / name
    wt.mkdir(parents=True, exist_ok=True)
    root_git = monorepo_root / ".git"
    root_git.mkdir(exist_ok=True)
    wt_git_dir = root_git / "worktrees" / name
    wt_git_dir.mkdir(parents=True, exist_ok=True)
    (wt / ".git").write_text(f"gitdir: {wt_git_dir}\n")
    return wt


def _make_subrepo_worktree(monorepo_root, area, name):
    """Create a worktree directory with a .git file pointing to a sub-repo."""
    wt = monorepo_root / ".workspace" / "worktrees" / area / name
    wt.mkdir(parents=True, exist_ok=True)
    subrepo_git = monorepo_root / area / ".git"
    subrepo_git.mkdir(parents=True, exist_ok=True)
    wt_git_dir = subrepo_git / "worktrees" / name
    wt_git_dir.mkdir(parents=True, exist_ok=True)
    (wt / ".git").write_text(f"gitdir: {wt_git_dir}\n")
    return wt


def test_detect_context_in_root(monorepo_root):
    result = detect_context(str(monorepo_root))
    assert result["inRootWorktree"] is False
    assert result["rootRepo"] == str(monorepo_root)
    assert result["worktreePath"] == ""


def test_detect_context_in_worktree(monorepo_root):
    wt = _make_root_worktree(monorepo_root, "dev-log-test")
    result = detect_context(str(wt))
    assert result["inRootWorktree"] is True
    assert result["rootRepo"] == str(monorepo_root)
    assert result["worktreePath"] == str(wt)


def test_detect_context_nested_in_worktree(monorepo_root):
    wt = _make_root_worktree(monorepo_root, "issue-42")
    docs = wt / "docs"
    docs.mkdir(parents=True)
    result = detect_context(str(docs))
    assert result["inRootWorktree"] is True
    assert result["rootRepo"] == str(monorepo_root)


def test_detect_context_client_worktree(monorepo_root):
    """Client area worktree should NOT be detected as root worktree."""
    wt = _make_subrepo_worktree(monorepo_root, "client", "issue-42")
    result = detect_context(str(wt))
    assert result["inRootWorktree"] is False
    assert result["rootRepo"] == str(monorepo_root)


def test_detect_context_server_worktree(monorepo_root):
    """Server area worktree should NOT be detected as root worktree."""
    wt = _make_subrepo_worktree(monorepo_root, "server", "issue-99")
    result = detect_context(str(wt))
    assert result["inRootWorktree"] is False
    assert result["rootRepo"] == str(monorepo_root)


def test_detect_context_no_git_file(monorepo_root):
    """Worktree path without .git file should fall through to standalone."""
    wt = monorepo_root / ".workspace" / "worktrees" / "no-git"
    wt.mkdir(parents=True)
    result = detect_context(str(wt))
    assert result["inRootWorktree"] is False


def test_detect_context_unknown_dir(tmp_path):
    result = detect_context(str(tmp_path))
    assert result["inRootWorktree"] is False
    assert result["rootRepo"] == str(tmp_path)
