"""Render startup entry point: initialise durable storage, rebuild, then serve."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from .app import serve


def workspace_root() -> Path:
    return Path(__file__).resolve().parents[2]


def seed_case_library(source: Path, destination: Path) -> None:
    """Seed an empty Render disk without overwriting cases saved by editors."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        shutil.copytree(source, destination)


def rebuild_site(root: Path) -> None:
    site_root = root / "architecture-case-site"
    environment = os.environ.copy()
    environment.setdefault("ARCHITECT_STATIC_ROOT", str(site_root / "public"))
    completed = subprocess.run(
        [sys.executable, str(site_root / "scripts" / "build_site.py")],
        cwd=site_root,
        env=environment,
        check=False,
    )
    if completed.returncode:
        raise SystemExit("Could not build the static site from the persistent case library.")


def main() -> None:
    root = workspace_root()
    data_root = Path(os.environ.get("ARCHITECT_DATA_ROOT", root / "tmp" / "runtime-data"))
    cases_root = Path(os.environ.setdefault("ARCHITECT_CASE_PACKAGES_ROOT", str(data_root / "case-packages")))
    os.environ.setdefault("ARCHITECT_JOBS_ROOT", str(data_root / "worker-jobs"))
    os.environ.setdefault("ARCHITECT_STATIC_ROOT", str(root / "architecture-case-site" / "public"))
    seed_case_library(root / "case-packages", cases_root)
    Path(os.environ["ARCHITECT_JOBS_ROOT"]).mkdir(parents=True, exist_ok=True)
    rebuild_site(root)
    serve()


if __name__ == "__main__":
    main()
