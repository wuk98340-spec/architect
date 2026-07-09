#!/usr/bin/env python3
"""Run package validation and optional quality scoring for an architecture case."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
VALIDATOR = Path(__file__).resolve().with_name("validate_case_package.py")
QUALITY_REVIEWER = ROOT / "scripts" / "review_case_quality.py"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case_folder", help="Case package folder or slug under case-packages/.")
    parser.add_argument("--output", type=Path, help="Write quality report to this path.")
    parser.add_argument("--skip-quality", action="store_true", help="Run only schema/package validation.")
    args = parser.parse_args()

    case_folder = resolve_case_folder(args.case_folder)
    if not case_folder.exists():
        print(f"ERROR: case folder does not exist: {case_folder}", file=sys.stderr)
        return 2

    validation = run([sys.executable, str(VALIDATOR), str(case_folder)])
    if validation != 0:
        return validation

    if args.skip_quality:
        return 0

    if not QUALITY_REVIEWER.exists():
        print(f"WARNING: quality reviewer not found: {QUALITY_REVIEWER}")
        return 0

    command = [sys.executable, str(QUALITY_REVIEWER), str(case_folder)]
    if args.output:
        command.extend(["--output", str(args.output)])
    return run(command)


def resolve_case_folder(value: str) -> Path:
    path = Path(value)
    if path.exists():
        return path
    return ROOT / "case-packages" / value


def run(command: list[str]) -> int:
    print("+ " + " ".join(command))
    result = subprocess.run(command, cwd=str(ROOT), text=True, check=False)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
