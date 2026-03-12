import re
from datetime import date
from pathlib import Path


def next_sequence(docs_dir: str, record_type: str) -> dict:
    """Scan directory for NNN-prefixed files, return max+1."""
    d = Path(docs_dir)
    prefix = "findings" if record_type == "findings" else "decision"
    pattern = re.compile(rf"^{prefix}[-.]?(\d{{3}})")

    max_seq = 0
    if d.exists():
        for f in d.iterdir():
            m = pattern.match(f.stem)
            if m:
                max_seq = max(max_seq, int(m.group(1)))

    next_val = max_seq + 1
    return {"next": next_val, "formatted": f"{next_val:03d}"}


def check_progress(docs_dir: str, target_date: str | None = None) -> dict:
    """Check if today's (or given date's) progress file exists."""
    d = Path(docs_dir) / "progress"
    dt = target_date or date.today().isoformat()
    filename = f"progress.{dt}.md"
    filepath = d / filename
    return {"exists": filepath.exists(), "path": str(filepath), "date": dt}
