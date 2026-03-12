from .command_runner import run


def worktree_add(
    repo_dir: str, worktree_path: str, branch: str, base: str = "main"
) -> None:
    run(["git", "-C", repo_dir, "worktree", "add", "-b", branch, worktree_path, base])


def worktree_remove(repo_dir: str, worktree_path: str) -> None:
    run(["git", "-C", repo_dir, "worktree", "remove", worktree_path])


def branch_delete(repo_dir: str, branch: str) -> None:
    run(["git", "-C", repo_dir, "branch", "-d", branch], check=False)


def fetch(repo_dir: str, remote: str = "origin", ref: str = "main") -> None:
    run(["git", "-C", repo_dir, "fetch", remote, ref])


def rebase(worktree: str, onto: str = "main") -> None:
    run(["git", "-C", worktree, "rebase", onto])


def rebase_abort(worktree: str) -> None:
    run(["git", "-C", worktree, "rebase", "--abort"], check=False)


def merge_ff_only(repo_dir: str, branch: str) -> None:
    run(["git", "-C", repo_dir, "merge", branch, "--ff-only"])


def add_docs(worktree: str) -> None:
    run(["git", "-C", worktree, "add", "docs/"])


def commit(worktree: str, message: str) -> str:
    run(["git", "-C", worktree, "commit", "-m", message])
    return run(["git", "-C", worktree, "rev-parse", "HEAD"]).stdout.strip()


def push(worktree: str) -> str:
    branch = current_branch(worktree)
    run(["git", "-C", worktree, "push", "origin", branch])
    return branch


def current_branch(repo_dir: str) -> str:
    return run(
        ["git", "-C", repo_dir, "rev-parse", "--abbrev-ref", "HEAD"]
    ).stdout.strip()


def rev_parse_head(repo_dir: str) -> str:
    return run(["git", "-C", repo_dir, "rev-parse", "HEAD"]).stdout.strip()
