import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from .paths import pipeline_state_dir


class MergeLockError(Exception):
    pass


class MergeLock:
    """TTL-based directory merge lock.

    Uses mkdir atomicity to acquire. No PID tracking.
    Stale locks (acquired_at older than stale_after seconds) are reclaimed.
    """

    def __init__(
        self,
        area: str,
        issue: int,
        monorepo_root: Path,
        max_wait: int = 300,
        stale_after: int = 1800,
    ):
        self.area = area
        self.issue = issue
        self.monorepo_root = monorepo_root
        self.max_wait = max_wait
        self.stale_after = stale_after
        self.lock_dir = pipeline_state_dir(area, monorepo_root) / "merge.lock"
        self._acquired = False

    def _now_epoch(self) -> int:
        return int(datetime.now(timezone.utc).timestamp())

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _try_mkdir(self) -> bool:
        try:
            self.lock_dir.mkdir(parents=False)
            return True
        except FileExistsError:
            return False

    def _write_owner(self) -> None:
        (self.lock_dir / "issue").write_text(str(self.issue))
        (self.lock_dir / "acquired").write_text(self._now_iso())

    def _read_file(self, name: str) -> str:
        try:
            return (self.lock_dir / name).read_text().strip()
        except Exception:
            return ""

    def _parse_epoch(self, ts: str) -> int:
        if not ts:
            return 0
        try:
            dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            return int(dt.timestamp())
        except Exception:
            return 0

    def _try_reclaim(self) -> bool:
        """Attempt to destroy the existing lock dir and re-acquire. Returns True on success."""
        try:
            shutil.rmtree(self.lock_dir)
        except Exception:
            pass
        if not self._try_mkdir():
            return False
        self._write_owner()
        # Verify we own it (guard against a race)
        time.sleep(0.2)
        return self._read_file("issue") == str(self.issue)

    def acquire(self) -> None:
        """Acquire the lock. Blocks up to max_wait seconds. Raises MergeLockError on timeout."""
        interval = 10
        waited = 0
        pipeline_state_dir(self.area, self.monorepo_root).mkdir(parents=True, exist_ok=True)

        while not self._try_mkdir():
            holder_issue = self._read_file("issue")
            acquired_ts = self._read_file("acquired")
            acquired_epoch = self._parse_epoch(acquired_ts)
            now_epoch = self._now_epoch()

            should_reclaim = False

            if acquired_epoch > 0:
                age = now_epoch - acquired_epoch
                if age >= self.stale_after:
                    print(
                        f"[merge_lock] stale merge lock detected for area={self.area} "
                        f"issue={holder_issue or 'unknown'}; reclaiming",
                        file=sys.stderr,
                    )
                    should_reclaim = True
            else:
                # No timestamp written yet; use dir mtime as fallback
                try:
                    dir_mtime = int(self.lock_dir.stat().st_mtime)
                    if (now_epoch - dir_mtime) >= 30:
                        print(
                            f"[merge_lock] incomplete merge lock (no timestamp after 30s) "
                            f"for area={self.area}; reclaiming",
                            file=sys.stderr,
                        )
                        should_reclaim = True
                except FileNotFoundError:
                    # Lock dir vanished between check and stat; retry immediately
                    continue

            if should_reclaim:
                if self._try_reclaim():
                    self._acquired = True
                    return
                # Race lost; fall through to wait loop
                continue

            if waited >= self.max_wait:
                raise MergeLockError(
                    f"[merge_lock] timeout after {self.max_wait}s "
                    f"(held by issue #{holder_issue or 'unknown'})"
                )

            print(
                f"[merge_lock] lock held for area={self.area} by issue "
                f"#{holder_issue or 'unknown'}; waiting ({waited}s/{self.max_wait}s)",
                file=sys.stderr,
            )
            time.sleep(interval)
            waited += interval

        self._write_owner()
        self._acquired = True

    def release(self, expected_issue: int = None) -> None:
        """Release the lock. Optionally verify ownership before releasing."""
        if not self.lock_dir.is_dir():
            return
        if expected_issue is not None:
            holder = self._read_file("issue")
            if holder and holder != str(expected_issue):
                raise MergeLockError(
                    f"[merge_lock] refusing to release lock for area={self.area}; "
                    f"expected issue #{expected_issue} but lock belongs to #{holder}"
                )
        shutil.rmtree(self.lock_dir, ignore_errors=True)
        self._acquired = False

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.release(expected_issue=self.issue)
        except Exception as e:
            print(f"[merge_lock] warning: release failed: {e}", file=sys.stderr)
        return False
