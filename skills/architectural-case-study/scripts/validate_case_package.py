#!/usr/bin/env python3
"""Validate an architecture case package folder."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_TOP_LEVEL = [
    "project_name",
    "architects",
    "location",
    "year",
    "program",
    "status",
    "case_type",
    "disambiguation_status",
    "disambiguation_candidates",
    "information_confidence",
    "incomplete_reason",
    "one_sentence_summary",
    "key_facts",
    "design_concept",
    "key_strategies",
    "spatial_ideas",
    "materials_structure",
    "site_context",
    "image_metadata",
    "download_mode",
    "sources",
    "uncertain_or_conflicting_info",
]

SOURCE_LEVELS = {"level_a", "level_b", "level_c", "level_d"}
HIGH_TRUST_LEVELS = {"level_a", "level_b"}
IMAGE_TYPES = {
    "01_hero",
    "02_site",
    "03_plan",
    "04_section",
    "05_elevation",
    "06_detail",
    "07_concept",
    "08_interior",
    "09_analysis",
}
DOWNLOAD_STATUSES = {"not_requested", "downloaded", "failed", "skipped"}


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: validate_case_package.py <case-package-folder>")
        return 2

    folder = Path(sys.argv[1])
    json_path = folder / "case.json"
    md_path = folder / "case.md"
    errors: list[str] = []
    warnings: list[str] = []
    strong_warnings: list[str] = []

    if not folder.exists():
        errors.append(f"Folder does not exist: {folder}")
        return finish(errors, warnings, strong_warnings)
    if not json_path.exists():
        errors.append(f"Missing {json_path}")
    if not md_path.exists():
        errors.append(f"Missing {md_path}")
    if errors:
        return finish(errors, warnings, strong_warnings)

    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"Invalid JSON in {json_path}: {exc}")
        return finish(errors, warnings, strong_warnings)

    if not isinstance(data, dict):
        errors.append("case.json must contain a JSON object")
        return finish(errors, warnings, strong_warnings)

    for key in REQUIRED_TOP_LEVEL:
        if key not in data:
            errors.append(f"case.json is missing top-level field '{key}'")

    if errors:
        return finish(errors, warnings, strong_warnings)

    if not isinstance(data["architects"], list):
        errors.append("'architects' must be an array")

    validate_enum(
        data.get("disambiguation_status"),
        {"confirmed", "high_confidence", "ambiguous_waiting_for_user", "not_needed"},
        "disambiguation_status",
        errors,
    )
    validate_enum(
        data.get("information_confidence"),
        {"high", "medium", "limited", "low"},
        "information_confidence",
        errors,
    )
    validate_enum(
        data.get("download_mode"),
        {"not_requested", "requested", "partial", "completed"},
        "download_mode",
        errors,
    )

    sources = validate_sources(data.get("sources"), errors, warnings, strong_warnings)
    source_ids = {source["id"] for source in sources if isinstance(source.get("id"), str)}
    image_ids = validate_images(data.get("image_metadata"), errors, warnings)

    validate_design_concept(data.get("design_concept"), source_ids, errors)
    validate_disambiguation_candidates(data.get("disambiguation_candidates"), errors)
    validate_key_facts(data.get("key_facts"), source_ids, errors, warnings)
    validate_strategies(data.get("key_strategies"), source_ids, image_ids, errors)

    for section in ["spatial_ideas", "materials_structure", "site_context"]:
        validate_notes(data.get(section), section, source_ids, image_ids, errors)

    validate_uncertainties(data.get("uncertain_or_conflicting_info"), source_ids, errors)

    if data.get("disambiguation_status") == "ambiguous_waiting_for_user":
        warnings.append("disambiguation_status is ambiguous_waiting_for_user; do not treat this as a complete case package.")

    if data.get("information_confidence") in {"limited", "low"} and not str(data.get("incomplete_reason", "")).strip():
        warnings.append("information_confidence is limited/low but incomplete_reason is empty.")

    return finish(errors, warnings, strong_warnings, folder)


def validate_sources(
    value: Any,
    errors: list[str],
    warnings: list[str],
    strong_warnings: list[str],
) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        errors.append("'sources' must be a non-empty array")
        return []

    source_ids: set[str] = set()
    levels: list[str] = []
    valid_sources: list[dict[str, Any]] = []

    for index, source in enumerate(value):
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
        if not isinstance(source_id, str) or not source_id.strip():
            errors.append(f"sources[{index}].id must be a non-empty string")
        elif source_id in source_ids:
            errors.append(f"Duplicate source id '{source_id}'")
        else:
            source_ids.add(source_id)

        level = source.get("source_level")
        if level not in SOURCE_LEVELS:
            errors.append(f"sources[{index}].source_level must be one of {sorted(SOURCE_LEVELS)}")
        else:
            levels.append(level)

        valid_sources.append(source)

    if levels:
        if not any(level in HIGH_TRUST_LEVELS for level in levels):
            warnings.append("Missing Level A/B sources; explain source limits in confidence or incomplete_reason.")
        if set(levels) <= {"level_c"}:
            warnings.append("Only Level C sources found; acceptable, but confidence should explain missing official or high-quality architecture media sources.")
        if set(levels) <= {"level_d"}:
            strong_warnings.append("Only Level D sources found; credibility is low and the package should be marked as preliminary.")

    return valid_sources


def validate_design_concept(value: Any, source_ids: set[str], errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append("'design_concept' must be an object")
        return
    require_keys(value, ["sourced_concept", "ai_synthesis", "source_ids"], "design_concept", errors)
    validate_source_refs(value.get("source_ids"), source_ids, "design_concept", errors)


def validate_disambiguation_candidates(value: Any, errors: list[str]) -> None:
    if not isinstance(value, list):
        errors.append("'disambiguation_candidates' must be an array")
        return
    required = [
        "candidate_project",
        "location",
        "architects",
        "year",
        "type",
        "main_sources",
        "confidence",
        "question_for_user",
    ]
    for index, candidate in enumerate(value):
        if not isinstance(candidate, dict):
            errors.append(f"disambiguation_candidates[{index}] must be an object")
            continue
        require_keys(candidate, required, f"disambiguation_candidates[{index}]", errors)
        if "main_sources" in candidate and not isinstance(candidate["main_sources"], list):
            errors.append(f"disambiguation_candidates[{index}].main_sources must be an array")


def validate_key_facts(value: Any, source_ids: set[str], errors: list[str], warnings: list[str]) -> None:
    if not isinstance(value, list):
        errors.append("'key_facts' must be an array")
        return
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            errors.append(f"key_facts[{index}] must be an object")
            continue
        require_keys(item, ["label", "value", "source_ids"], f"key_facts[{index}]", errors)
        source_ref_count = validate_source_refs(item.get("source_ids"), source_ids, f"key_facts[{index}]", errors)
        if source_ref_count == 0:
            warnings.append(f"key_facts[{index}] has no evidence source; key facts should cite sources.")


def validate_strategies(value: Any, source_ids: set[str], image_ids: set[str], errors: list[str]) -> None:
    if not isinstance(value, list):
        errors.append("'key_strategies' must be an array")
        return
    if not 3 <= len(value) <= 5:
        errors.append("'key_strategies' must contain 3 to 5 items")
    required = [
        "strategy_name",
        "design_problem",
        "specific_approach",
        "architectural_effect",
        "evidence",
        "source_ids",
        "related_image_ids",
        "transferable_lesson",
    ]
    for index, strategy in enumerate(value):
        if not isinstance(strategy, dict):
            errors.append(f"key_strategies[{index}] must be an object")
            continue
        require_keys(strategy, required, f"key_strategies[{index}]", errors)
        if not str(strategy.get("evidence", "")).strip():
            errors.append(f"key_strategies[{index}].evidence must not be empty")
        if validate_source_refs(strategy.get("source_ids"), source_ids, f"key_strategies[{index}]", errors) == 0:
            errors.append(f"key_strategies[{index}] must reference at least one source")
        validate_image_refs(strategy.get("related_image_ids"), image_ids, f"key_strategies[{index}]", errors)


def validate_notes(
    value: Any,
    label: str,
    source_ids: set[str],
    image_ids: set[str],
    errors: list[str],
) -> None:
    if not isinstance(value, list):
        errors.append(f"'{label}' must be an array")
        return
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            errors.append(f"{label}[{index}] must be an object")
            continue
        require_keys(item, ["text", "source_ids", "related_image_ids"], f"{label}[{index}]", errors)
        validate_source_refs(item.get("source_ids"), source_ids, f"{label}[{index}]", errors)
        validate_image_refs(item.get("related_image_ids"), image_ids, f"{label}[{index}]", errors)


def validate_images(value: Any, errors: list[str], warnings: list[str]) -> set[str]:
    if not isinstance(value, list):
        errors.append("'image_metadata' must be an array")
        return set()

    image_ids: set[str] = set()
    required = [
        "id",
        "file_name",
        "image_type",
        "source_url",
        "source_site",
        "caption",
        "copyright_note",
        "recommended_use",
        "related_sections",
        "download_status",
        "failure_reason",
    ]
    for index, image in enumerate(value):
        if not isinstance(image, dict):
            errors.append(f"image_metadata[{index}] must be an object")
            continue
        require_keys(image, required, f"image_metadata[{index}]", errors)

        image_id = image.get("id")
        if not isinstance(image_id, str) or not image_id.strip():
            errors.append(f"image_metadata[{index}].id must be a non-empty string")
        elif image_id in image_ids:
            errors.append(f"Duplicate image id '{image_id}'")
        else:
            image_ids.add(image_id)

        if image.get("image_type") not in IMAGE_TYPES:
            errors.append(f"image_metadata[{index}].image_type must be one of {sorted(IMAGE_TYPES)}")
        if image.get("download_status") not in DOWNLOAD_STATUSES:
            errors.append(f"image_metadata[{index}].download_status must be one of {sorted(DOWNLOAD_STATUSES)}")
        if image.get("download_status") == "failed" and not str(image.get("failure_reason", "")).strip():
            errors.append(f"image_metadata[{index}] download failed but failure_reason is empty")
        if not str(image.get("source_url", "")).strip():
            errors.append(f"image_metadata[{index}].source_url must not be empty")
        if not str(image.get("source_site", "")).strip():
            errors.append(f"image_metadata[{index}].source_site must not be empty")
        if not str(image.get("copyright_note", "")).strip():
            warnings.append(f"image_metadata[{index}].copyright_note is empty")
        if "related_sections" in image and not isinstance(image["related_sections"], list):
            errors.append(f"image_metadata[{index}].related_sections must be an array")

    return image_ids


def validate_uncertainties(value: Any, source_ids: set[str], errors: list[str]) -> None:
    if not isinstance(value, list):
        errors.append("'uncertain_or_conflicting_info' must be an array")
        return
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            errors.append(f"uncertain_or_conflicting_info[{index}] must be an object")
            continue
        require_keys(item, ["topic", "description", "source_ids"], f"uncertain_or_conflicting_info[{index}]", errors)
        validate_source_refs(item.get("source_ids"), source_ids, f"uncertain_or_conflicting_info[{index}]", errors)


def require_keys(item: dict[str, Any], keys: list[str], label: str, errors: list[str]) -> None:
    for key in keys:
        if key not in item:
            errors.append(f"{label} is missing required key '{key}'")


def validate_enum(value: Any, allowed: set[str], label: str, errors: list[str]) -> None:
    if value not in allowed:
        errors.append(f"'{label}' must be one of {sorted(allowed)}")


def validate_source_refs(value: Any, source_ids: set[str], label: str, errors: list[str]) -> int:
    if not isinstance(value, list):
        errors.append(f"{label}.source_ids must be an array")
        return 0
    valid_count = 0
    for source_id in value:
        if source_id not in source_ids:
            errors.append(f"{label} references unknown source id '{source_id}'")
        else:
            valid_count += 1
    return valid_count


def validate_image_refs(value: Any, image_ids: set[str], label: str, errors: list[str]) -> int:
    if not isinstance(value, list):
        errors.append(f"{label}.related_image_ids must be an array")
        return 0
    valid_count = 0
    for image_id in value:
        if image_id not in image_ids:
            errors.append(f"{label} references unknown image id '{image_id}'")
        else:
            valid_count += 1
    return valid_count


def finish(
    errors: list[str],
    warnings: list[str],
    strong_warnings: list[str],
    folder: Path | None = None,
) -> int:
    for error in errors:
        print(f"ERROR: {error}")
    for warning in warnings:
        print(f"WARNING: {warning}")
    for warning in strong_warnings:
        print(f"STRONG WARNING: {warning}")

    if errors:
        return 1

    if folder is None:
        print("OK: validation completed with no blocking errors.")
    elif warnings or strong_warnings:
        print(f"OK: {folder} has no blocking errors, but review warnings above.")
    else:
        print(f"OK: {folder} is a valid architecture case package.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
