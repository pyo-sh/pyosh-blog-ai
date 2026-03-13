"""CLI entry point for the agent-tracker Python backend.

Usage:
    python3 -m backend [options]
    PYTHONPATH=tools/agent-tracker python3 -m backend [options]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

DEFAULTS = {
    "session": "lab",
    "sidecar_dir": ".workspace/agent-tracker",
    "orch_dir": ".workspace/orchestrate",
    "pipeline_dir": ".workspace/pipeline",
    "output": ".workspace/agent-tracker/state/current.json",
    "interval": 0,
}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="agent-tracker Python backend: collect and export normalized snapshot"
    )
    parser.add_argument(
        "--session",
        default=DEFAULTS["session"],
        help="tmux session name (default: lab)",
    )
    parser.add_argument(
        "--sidecar-dir",
        default=DEFAULTS["sidecar_dir"],
        help="sidecar directory relative to root (default: .workspace/agent-tracker)",
    )
    parser.add_argument(
        "--orch-dir",
        default=DEFAULTS["orch_dir"],
        help="orchestrator directory relative to root (default: .workspace/orchestrate)",
    )
    parser.add_argument(
        "--pipeline-dir",
        default=DEFAULTS["pipeline_dir"],
        help="pipeline state directory relative to root (default: .workspace/pipeline)",
    )
    parser.add_argument(
        "--output",
        default=DEFAULTS["output"],
        help="output path for current.json (default: .workspace/agent-tracker/state/current.json)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=DEFAULTS["interval"],
        help="refresh interval in seconds; 0 = run once (default: 0)",
    )
    parser.add_argument(
        "--root",
        default=None,
        help="monorepo root directory (default: auto-detected via .agents/)",
    )
    parser.add_argument(
        "--print",
        dest="print_output",
        action="store_true",
        help="print snapshot JSON to stdout after each collection",
    )
    args = parser.parse_args()

    root = Path(args.root) if args.root else _find_monorepo_root()

    sidecar_dir = _resolve(args.sidecar_dir, root)
    orch_dir = _resolve(args.orch_dir, root)
    pipeline_dir = _resolve(args.pipeline_dir, root)
    output_path = _resolve(args.output, root)

    from .exporter import run_once

    if args.interval > 0:
        while True:
            try:
                _run(args.session, sidecar_dir, orch_dir, pipeline_dir, output_path,
                     args.print_output, run_once)
            except KeyboardInterrupt:
                break
            except Exception as exc:
                print(f"[agent-tracker] error: {exc}", file=sys.stderr)
            time.sleep(args.interval)
    else:
        _run(args.session, sidecar_dir, orch_dir, pipeline_dir, output_path,
             args.print_output, run_once)


def _run(session, sidecar_dir, orch_dir, pipeline_dir, output_path, print_output, run_once):
    snap = run_once(session, sidecar_dir, orch_dir, pipeline_dir, output_path)
    if print_output:
        print(json.dumps(snap.to_dict(), indent=2, ensure_ascii=False))


def _resolve(path_str: str, base: Path) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else base / p


def _find_monorepo_root() -> Path:
    """Walk up from this file looking for the .agents/ directory."""
    for parent in Path(__file__).resolve().parents:
        if (parent / ".agents").exists():
            return parent
    return Path.cwd()


if __name__ == "__main__":
    main()
