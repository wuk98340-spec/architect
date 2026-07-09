#!/usr/bin/env python3
"""Back up an architecture case package before local repair."""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9._-]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value or "repair"


def resolve_image_path(folder: Path, image: str) -> Path:
    image_path = Path(image)
    if image_path.is_absolute():
        return image_path
    return folder / image_path


def ensure_inside_folder(folder: Path, path: Path) -> None:
    try:
        path.resolve().relative_to(folder.resolve())
    except ValueError:
        raise ValueError(f"Image path is outside the case package: {path}") from None


def copy_required_file(source: Path, destination: Path) -> None:
    if not source.exists():
        raise FileNotFoundError(f"Required file not found: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def copy_optional_image(folder: Path, image: str, revision_folder: Path) -> str:
    source = resolve_image_path(folder, image)
    ensure_inside_folder(folder, source)
    if not source.exists():
        raise FileNotFoundError(f"Image not found: {source}")
    relative = source.resolve().relative_to(folder.resolve())
    destination = revision_folder / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return str(relative).replace("\\", "/")


def backup_case_package(folder: Path, label: str, images: list[str]) -> Path:
    folder = folder.resolve()
    if not folder.exists() or not folder.is_dir():
        raise FileNotFoundError(f"Case package folder not found: {folder}")

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    revision_folder = folder / "revisions" / f"{timestamp}-{slugify(label)}"
    if revision_folder.exists():
        raise FileExistsError(f"Backup folder already exists: {revision_folder}")

    copy_required_file(folder / "case.md", revision_folder / "case.md")
    copy_required_file(folder / "case.json", revision_folder / "case.json")

    copied_images: list[str] = []
    for image in images:
        copied_images.append(copy_optional_image(folder, image, revision_folder))

    manifest_lines = [
        f"created_at: {timestamp}",
        f"label: {slugify(label)}",
        "files:",
        "- case.md",
        "- case.json",
    ]
    manifest_lines.extend(f"- {image}" for image in copied_images)
    (revision_folder / "backup-manifest.txt").write_text(
        "\n".join(manifest_lines) + "\n",
        encoding="utf-8",
    )

    return revision_folder


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Back up case.md, case.json, and optional images before local repair.",
    )
    parser.add_argument("case_folder", help="Path to a case package folder.")
    parser.add_argument(
        "--label",
        default="repair",
        help="Short label for the revision folder. Defaults to 'repair'.",
    )
    parser.add_argument(
        "--image",
        action="append",
        default=[],
        help="Relative or absolute path to an image inside the case package. May be repeated.",
    )
    args = parser.parse_args()

    try:
        revision_folder = backup_case_package(Path(args.case_folder), args.label, args.image)
    except Exception as exc:  # noqa: BLE001 - command-line tool should print concise failures.
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(revision_folder)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
