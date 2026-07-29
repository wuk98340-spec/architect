"""Render startup entry point: initialise durable storage, rebuild, then serve."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from .app import serve
from .cos_storage import cos_failure_message, current_cos_mirror


def workspace_root() -> Path:
    return Path(__file__).resolve().parents[2]


def seed_case_library(source: Path, destination: Path) -> None:
    """Seed when COS did not provide an actual case package."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)


def has_case_library(root: Path) -> bool:
    """An empty directory created by a failed COS sync is not a library."""
    return root.is_dir() and any(root.rglob("case.json"))


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
    try:
        cos_mirror = current_cos_mirror()
        if cos_mirror:
            print(cos_mirror.diagnostic_log(), file=sys.stderr)
        library_exists = cos_mirror.hydrate_library(case_packages_root=cases_root) if cos_mirror else has_case_library(cases_root)
    except Exception as error:
        # Storage must not make the public API unavailable.  A failed optional
        # mirror (bad credentials, a transient COS error, etc.) falls back to
        # the case library baked into the deployed image.
        message = cos_failure_message(error)
        print(f"{message} Starting with bundled case library.", file=sys.stderr)
        os.environ["ARCHITECT_COS_STORAGE_UNAVAILABLE"] = message
        cos_mirror = None
        library_exists = has_case_library(cases_root)
    if not library_exists:
        seed_case_library(root / "case-packages", cases_root)
    if cos_mirror and not library_exists:
        # The first deployment seeds only the bundled baseline packages. Later
        # starts hydrate the existing COS library and do not overwrite it.
        for package in cases_root.iterdir():
            if package.is_dir():
                cos_mirror.persist_case_package(case_packages_root=cases_root, package_slug=package.name)
    Path(os.environ["ARCHITECT_JOBS_ROOT"]).mkdir(parents=True, exist_ok=True)
    rebuild_site(root)
    serve()


if __name__ == "__main__":
    main()
