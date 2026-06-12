#!/usr/bin/env python3
"""Validate an architecture case package folder."""

from __future__ import annotations

import json
import sys
from pathlib import Path


REQUIRED_TOP_LEVEL = [
    "project_name",
    "architects",
    "location",
    "year",
    "program",
    "status",
    "one_sentence_summary",
    "key_facts",
    "design_strategies",
    "spatial_ideas",
    "materials_structure",
    "site_context",
    "image_links",
    "sources",
    "uncertain_or_conflicting_info",
]

SOURCE_LEVELS = {"official", "architecture_media", "general_media", "reference_only"}


def fail(errors: list[str]) -> int:
    for error in errors:
        print(f"ERROR: {error}")
    return 1


def require_keys(item: dict, keys: list[str], label: str, errors: list[str]) -> None:
    for key in keys:
        if key not in item:
            errors.append(f"{label} is missing required key '{key}'")


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: validate_case_package.py <case-package-folder>")
        return 2

    folder = Path(sys.argv[1])
    json_path = folder / "case.json"
    md_path = folder / "case.md"
    errors: list[str] = []

    if not folder.exists():
        return fail([f"Folder does not exist: {folder}"])
    if not json_path.exists():
        errors.append(f"Missing {json_path}")
    if not md_path.exists():
        errors.append(f"Missing {md_path}")
    if errors:
        return fail(errors)

    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return fail([f"Invalid JSON in {json_path}: {exc}"])

    for key in REQUIRED_TOP_LEVEL:
        if key not in data:
            errors.append(f"case.json is missing top-level field '{key}'")

    if errors:
        return fail(errors)

    if not isinstance(data["architects"], list):
        errors.append("'architects' must be an array")

    sources = data["sources"]
    if not isinstance(sources, list) or not sources:
        errors.append("'sources' must be a non-empty array")
        sources = []

    source_ids: set[str] = set()
    non_reference_count = 0
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            errors.append(f"sources[{index}] must be an object")
            continue
        require_keys(
            source,
            ["id", "title", "url", "source_level", "publisher", "accessed_date", "notes"],
            f"sources[{index}]",
            errors,
        )
        source_id = source.get("id")
        if source_id:
            if source_id in source_ids:
                errors.append(f"Duplicate source id '{source_id}'")
            source_ids.add(source_id)
        level = source.get("source_level")
        if level not in SOURCE_LEVELS:
            errors.append(f"sources[{index}].source_level must be one of {sorted(SOURCE_LEVELS)}")
        elif level != "reference_only":
            non_reference_count += 1

    if sources and non_reference_count == 0:
        errors.append("At least one source must be official, architecture_media, or general_media")

    strategies = data["design_strategies"]
    if not isinstance(strategies, list) or len(strategies) < 3:
        errors.append("'design_strategies' must contain at least 3 items")
    elif isinstance(strategies, list):
        for index, strategy in enumerate(strategies):
            if not isinstance(strategy, dict):
                errors.append(f"design_strategies[{index}] must be an object")
                continue
            require_keys(
                strategy,
                ["title", "description", "evidence", "source_ids"],
                f"design_strategies[{index}]",
                errors,
            )
            validate_source_refs(strategy.get("source_ids"), source_ids, f"design_strategies[{index}]", errors)

    for section in ["key_facts", "spatial_ideas", "materials_structure", "site_context"]:
        items = data[section]
        if not isinstance(items, list):
            errors.append(f"'{section}' must be an array")
            continue
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                errors.append(f"{section}[{index}] must be an object")
                continue
            expected = ["label", "value", "source_ids"] if section == "key_facts" else ["text", "source_ids"]
            require_keys(item, expected, f"{section}[{index}]", errors)
            validate_source_refs(item.get("source_ids"), source_ids, f"{section}[{index}]", errors)

    image_links = data["image_links"]
    if not isinstance(image_links, list):
        errors.append("'image_links' must be an array")
    else:
        for index, image in enumerate(image_links):
            if not isinstance(image, dict):
                errors.append(f"image_links[{index}] must be an object")
                continue
            require_keys(
                image,
                ["url", "source_id", "intended_use", "copyright_note"],
                f"image_links[{index}]",
                errors,
            )
            validate_source_refs([image.get("source_id")], source_ids, f"image_links[{index}]", errors)

    uncertainties = data["uncertain_or_conflicting_info"]
    if not isinstance(uncertainties, list):
        errors.append("'uncertain_or_conflicting_info' must be an array")
    else:
        for index, item in enumerate(uncertainties):
            if not isinstance(item, dict):
                errors.append(f"uncertain_or_conflicting_info[{index}] must be an object")
                continue
            require_keys(
                item,
                ["topic", "description", "source_ids"],
                f"uncertain_or_conflicting_info[{index}]",
                errors,
            )
            validate_source_refs(item.get("source_ids"), source_ids, f"uncertain_or_conflicting_info[{index}]", errors)

    if errors:
        return fail(errors)

    print(f"OK: {folder} is a valid architecture case package.")
    return 0


def validate_source_refs(value, source_ids: set[str], label: str, errors: list[str]) -> None:
    if not isinstance(value, list):
        errors.append(f"{label}.source_ids must be an array")
        return
    for source_id in value:
        if source_id not in source_ids:
            errors.append(f"{label} references unknown source id '{source_id}'")


if __name__ == "__main__":
    raise SystemExit(main())
