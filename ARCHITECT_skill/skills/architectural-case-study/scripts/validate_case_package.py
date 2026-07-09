#!/usr/bin/env python3
"""Validate an architecture case package folder."""

from __future__ import annotations

import json
import re
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
    "source_quality",
    "sources",
    "uncertain_or_conflicting_info",
]

SOURCE_LEVELS = {"level_a", "level_b", "level_c", "level_d"}
HIGH_TRUST_LEVELS = {"level_a", "level_b"}
SOURCE_MODES = {"web", "pdf", "mixed"}
SOURCE_KINDS = {"web", "user_pdf", "local_pdf", "local_file"}
PDF_SOURCE_KINDS = {"user_pdf", "local_pdf"}
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
SOURCE_SUFFICIENCY_STATUSES = {"sufficient", "partial", "insufficient", "ambiguous"}
ANALYSIS_COVERAGE_VALUES = {
    "concept",
    "context",
    "program",
    "circulation",
    "facade_material",
    "structure_construction",
    "user_experience",
    "urban_relationship",
}
EXTENDED_TOP_LEVEL = [
    "technical_metrics",
    "site_information",
    "conceptual_exploration",
    "architectural_language_generation",
    "construction_quality_control",
    "design_lessons",
]
EVIDENCE_TYPES = {"sourced", "synthesis", "missing", "conflict"}
METRIC_CONFIDENCE_VALUES = {"confirmed", "reported", "limited", "unknown", "conflicting"}


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

    try:
        md_text = md_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        errors.append(f"Invalid UTF-8 in {md_path}: {exc}")
        return finish(errors, warnings, strong_warnings)

    if not isinstance(data, dict):
        errors.append("case.json must contain a JSON object")
        return finish(errors, warnings, strong_warnings)

    for key in REQUIRED_TOP_LEVEL:
        if key not in data:
            errors.append(f"case.json is missing top-level field '{key}'")

    if not isinstance(data.get("architects"), list):
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
    if "source_mode" in data:
        validate_enum(data.get("source_mode"), SOURCE_MODES, "source_mode", errors)

    sources = validate_sources(data.get("sources"), errors, warnings, strong_warnings)
    source_ids = {source["id"] for source in sources if isinstance(source.get("id"), str)}
    image_ids = validate_images(data.get("image_metadata"), data.get("download_mode"), errors, warnings)
    validate_image_completion_policy(data, errors, warnings)

    validate_source_quality(data, source_ids, errors, warnings)
    validate_design_concept(data.get("design_concept"), source_ids, errors)
    validate_disambiguation_candidates(data.get("disambiguation_candidates"), errors)
    validate_key_facts(data.get("key_facts"), source_ids, errors, warnings)
    validate_strategies(data.get("key_strategies"), source_ids, image_ids, errors)

    for section in ["spatial_ideas", "materials_structure", "site_context"]:
        validate_notes(data.get(section), section, source_ids, image_ids, errors)

    validate_markdown_image_usage(
        data.get("image_metadata"),
        data.get("download_mode"),
        md_text,
        folder,
        errors,
        warnings,
        strong_warnings,
    )
    validate_uncertainties(data.get("uncertain_or_conflicting_info"), source_ids, errors)
    validate_extended_fields(data, source_ids, image_ids, errors, warnings)
    validate_pdf_source_mode(data, sources, source_ids, folder, errors, warnings)

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

        source_kind = source.get("source_kind")
        if source_kind is not None and source_kind not in SOURCE_KINDS:
            errors.append(f"sources[{index}].source_kind must be one of {sorted(SOURCE_KINDS)}")

        if "file_path" in source and not isinstance(source["file_path"], str):
            errors.append(f"sources[{index}].file_path must be a string")

        if "page_count" in source and (type(source["page_count"]) is not int or source["page_count"] < 1):
            errors.append(f"sources[{index}].page_count must be a positive integer")

        if "bibliographic_note" in source and not isinstance(source["bibliographic_note"], str):
            errors.append(f"sources[{index}].bibliographic_note must be a string")

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


def validate_pdf_source_mode(
    data: dict[str, Any],
    sources: list[dict[str, Any]],
    source_ids: set[str],
    folder: Path,
    errors: list[str],
    warnings: list[str],
) -> None:
    source_mode = data.get("source_mode", "web")
    pdf_sources = [source for source in sources if is_pdf_source(source)]
    pdf_source_ids = {
        str(source.get("id"))
        for source in pdf_sources
        if isinstance(source.get("id"), str) and source.get("id")
    }

    if source_mode == "pdf" and not pdf_sources:
        errors.append("source_mode is pdf, but sources[] contains no PDF source.")
    if source_mode == "mixed" and not pdf_sources:
        errors.append("source_mode is mixed, but sources[] contains no PDF source.")
    if source_mode == "mixed" and pdf_sources and len(pdf_sources) == len(sources):
        warnings.append("source_mode is mixed, but all sources appear to be PDFs; use pdf unless web/local non-PDF sources are used.")
    if source_mode == "pdf" and pdf_sources and len(pdf_sources) != len(sources):
        warnings.append("source_mode is pdf, but sources[] includes non-PDF sources; use mixed if those sources support the package.")

    for index, source in enumerate(pdf_sources):
        label = f"sources[{sources.index(source)}]"
        file_path = source.get("file_path")
        if not isinstance(file_path, str) or not file_path.strip():
            errors.append(f"{label}.file_path is required for PDF sources.")
            continue
        if not file_path.lower().endswith(".pdf"):
            warnings.append(f"{label}.file_path does not end with .pdf: {file_path}")
        source_path = (folder / file_path).resolve()
        folder_path = folder.resolve()
        try:
            source_path.relative_to(folder_path)
        except ValueError:
            errors.append(f"{label}.file_path must stay inside the case package folder: {file_path}")
            continue
        if source_mode in {"pdf", "mixed"} and not source_path.exists():
            errors.append(f"{label}.file_path does not exist: {file_path}")

        if type(source.get("page_count")) is not int or source.get("page_count", 0) < 1:
            errors.append(f"{label}.page_count is required as a positive integer for PDF sources.")

    evidence_spans = data.get("evidence_spans")
    if evidence_spans is None:
        if source_mode in {"pdf", "mixed"}:
            errors.append("evidence_spans is required when source_mode is pdf or mixed.")
        return

    valid_spans = validate_evidence_spans(evidence_spans, source_ids, pdf_source_ids, sources, source_mode, errors)
    if source_mode not in {"pdf", "mixed"}:
        return

    if not valid_spans:
        errors.append("PDF source mode requires at least one valid evidence_spans[] item.")
        return

    supported_targets = {
        support
        for span in valid_spans
        for support in span.get("supports", [])
        if isinstance(support, str)
    }
    if not any(target.startswith("key_facts") for target in supported_targets):
        errors.append("PDF source mode requires page evidence supporting key_facts.")
    if not any(target.startswith("design_concept") for target in supported_targets):
        errors.append("PDF source mode requires page evidence supporting design_concept.")

    strategy_support_count = len(
        {
            target
            for target in supported_targets
            if target.startswith("key_strategies")
        }
    )
    strategy_count = len(data.get("key_strategies", [])) if isinstance(data.get("key_strategies"), list) else 0
    required_strategy_support = min(3, strategy_count)
    if strategy_support_count < required_strategy_support:
        errors.append(
            "PDF source mode requires page evidence for at least "
            f"{required_strategy_support} key_strategies items."
        )


def validate_evidence_spans(
    value: Any,
    source_ids: set[str],
    pdf_source_ids: set[str],
    sources: list[dict[str, Any]],
    source_mode: Any,
    errors: list[str],
) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        errors.append("evidence_spans must be an array")
        return []

    source_by_id = {
        source.get("id"): source
        for source in sources
        if isinstance(source.get("id"), str)
    }
    span_ids: set[str] = set()
    valid_spans: list[dict[str, Any]] = []
    required = ["id", "source_id", "page_start", "page_end", "evidence_type", "quote_or_summary", "supports", "notes"]

    for index, span in enumerate(value):
        if not isinstance(span, dict):
            errors.append(f"evidence_spans[{index}] must be an object")
            continue
        require_keys(span, required, f"evidence_spans[{index}]", errors)

        span_id = span.get("id")
        if not isinstance(span_id, str) or not span_id.strip():
            errors.append(f"evidence_spans[{index}].id must be a non-empty string")
        elif span_id in span_ids:
            errors.append(f"Duplicate evidence span id '{span_id}'")
        else:
            span_ids.add(span_id)

        source_id = span.get("source_id")
        if source_id not in source_ids:
            errors.append(f"evidence_spans[{index}] references unknown source id '{source_id}'")
        elif source_mode in {"pdf", "mixed"} and source_id not in pdf_source_ids:
            errors.append(f"evidence_spans[{index}].source_id must reference a PDF source in PDF source mode")

        for key in ["page_start", "page_end"]:
            if type(span.get(key)) is not int or span.get(key) < 1:
                errors.append(f"evidence_spans[{index}].{key} must be a positive integer")

        page_start = span.get("page_start")
        page_end = span.get("page_end")
        if type(page_start) is int and type(page_end) is int and page_end < page_start:
            errors.append(f"evidence_spans[{index}].page_end must be greater than or equal to page_start")

        source = source_by_id.get(source_id)
        page_count = source.get("page_count") if isinstance(source, dict) else None
        if type(page_count) is int and type(page_end) is int and page_end > page_count:
            errors.append(
                f"evidence_spans[{index}].page_end exceeds page_count for source '{source_id}'"
            )

        if span.get("evidence_type") not in EVIDENCE_TYPES:
            errors.append(f"evidence_spans[{index}].evidence_type must be one of {sorted(EVIDENCE_TYPES)}")
        if not isinstance(span.get("quote_or_summary"), str) or not span.get("quote_or_summary", "").strip():
            errors.append(f"evidence_spans[{index}].quote_or_summary must be a non-empty string")
        if not isinstance(span.get("notes"), str):
            errors.append(f"evidence_spans[{index}].notes must be a string")
        supports = span.get("supports")
        if not isinstance(supports, list) or not supports:
            errors.append(f"evidence_spans[{index}].supports must be a non-empty array")
        elif any(not isinstance(item, str) or not item.strip() for item in supports):
            errors.append(f"evidence_spans[{index}].supports items must be non-empty strings")

        valid_spans.append(span)

    return valid_spans


def is_pdf_source(source: dict[str, Any]) -> bool:
    source_kind = source.get("source_kind")
    file_path = str(source.get("file_path") or "")
    url = str(source.get("url") or "")
    return source_kind in PDF_SOURCE_KINDS or file_path.lower().endswith(".pdf") or url.lower().endswith(".pdf")


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


def validate_source_quality(
    data: dict[str, Any],
    source_ids: set[str],
    errors: list[str],
    warnings: list[str],
) -> None:
    value = data.get("source_quality")
    if not isinstance(value, dict):
        errors.append("'source_quality' must be an object")
        return

    required = [
        "has_primary_sources",
        "primary_sources_used_for_identity",
        "architecture_media_count",
        "wechat_valid_result_count",
        "zhihu_valid_result_count",
        "source_sufficiency_status",
        "secondary_source_heavy",
        "manual_review_needed",
        "identity_confirming_source_ids",
        "analysis_coverage",
    ]
    require_keys(value, required, "source_quality", errors)

    for key in ["has_primary_sources", "primary_sources_used_for_identity", "secondary_source_heavy"]:
        if key in value and type(value[key]) is not bool:
            errors.append(f"source_quality.{key} must be a boolean")

    for key in ["architecture_media_count", "wechat_valid_result_count", "zhihu_valid_result_count"]:
        if key not in value:
            continue
        if type(value[key]) is not int or value[key] < 0:
            errors.append(f"source_quality.{key} must be a non-negative integer")

    status = value.get("source_sufficiency_status")
    if status not in SOURCE_SUFFICIENCY_STATUSES:
        errors.append(f"source_quality.source_sufficiency_status must be one of {sorted(SOURCE_SUFFICIENCY_STATUSES)}")

    if "manual_review_needed" in value and not isinstance(value["manual_review_needed"], list):
        errors.append("source_quality.manual_review_needed must be an array")
    elif isinstance(value.get("manual_review_needed"), list):
        for index, item in enumerate(value["manual_review_needed"]):
            if not isinstance(item, str):
                errors.append(f"source_quality.manual_review_needed[{index}] must be a string")

    identity_refs = value.get("identity_confirming_source_ids")
    if not isinstance(identity_refs, list):
        errors.append("source_quality.identity_confirming_source_ids must be an array")
        identity_count = 0
    else:
        identity_count = 0
        for index, source_id in enumerate(identity_refs):
            if source_id not in source_ids:
                errors.append(
                    f"source_quality.identity_confirming_source_ids[{index}] references unknown source id '{source_id}'"
                )
            else:
                identity_count += 1

    coverage = value.get("analysis_coverage")
    if not isinstance(coverage, list):
        errors.append("source_quality.analysis_coverage must be an array")
        coverage_count = 0
    else:
        coverage_count = len(coverage)
        seen_coverage: set[str] = set()
        for index, item in enumerate(coverage):
            if item not in ANALYSIS_COVERAGE_VALUES:
                errors.append(
                    f"source_quality.analysis_coverage[{index}] must be one of {sorted(ANALYSIS_COVERAGE_VALUES)}"
                )
            elif item in seen_coverage:
                warnings.append(f"source_quality.analysis_coverage contains duplicate value '{item}'")
            else:
                seen_coverage.add(item)

    if status == "insufficient":
        if value.get("secondary_source_heavy") is not True:
            errors.append("source_quality.secondary_source_heavy must be true when source_sufficiency_status is insufficient")
        if not str(data.get("incomplete_reason", "")).strip():
            errors.append("incomplete_reason must not be empty when source_sufficiency_status is insufficient")

    if status == "ambiguous" and data.get("disambiguation_status") != "ambiguous_waiting_for_user":
        errors.append(
            "disambiguation_status must be ambiguous_waiting_for_user when source_sufficiency_status is ambiguous"
        )

    if status == "sufficient":
        if coverage_count < 3:
            errors.append("source_quality.analysis_coverage must contain at least 3 items when status is sufficient")
        if identity_count < 2:
            errors.append(
                "source_quality.identity_confirming_source_ids must reference at least 2 sources when status is sufficient"
            )


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


def validate_images(value: Any, download_mode: Any, errors: list[str], warnings: list[str]) -> set[str]:
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
        if image.get("download_status") == "skipped" and not str(image.get("failure_reason", "")).strip():
            errors.append(f"image_metadata[{index}] download skipped but failure_reason is empty")
        if image.get("download_status") == "downloaded" and not str(image.get("file_name", "")).strip():
            errors.append(f"image_metadata[{index}] is downloaded but file_name is empty")
        if download_mode in {"completed", "partial"} and image.get("download_status") == "not_requested":
            warnings.append(
                f"image_metadata[{index}] is not_requested while download_mode is {download_mode}; use downloaded, failed, or skipped."
            )
        if not str(image.get("source_url", "")).strip():
            errors.append(f"image_metadata[{index}].source_url must not be empty")
        if not str(image.get("source_site", "")).strip():
            errors.append(f"image_metadata[{index}].source_site must not be empty")
        if not str(image.get("copyright_note", "")).strip():
            warnings.append(f"image_metadata[{index}].copyright_note is empty")
        if not str(image.get("relevance_reason", "")).strip():
            warnings.append(
                f"image_metadata[{index}].relevance_reason is empty; new packages should explain the exact text-image relationship."
            )
        if "related_sections" in image and not isinstance(image["related_sections"], list):
            errors.append(f"image_metadata[{index}].related_sections must be an array")

    return image_ids


def validate_image_completion_policy(data: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    download_mode = data.get("download_mode")
    images = data.get("image_metadata")
    incomplete_reason = str(data.get("incomplete_reason", "")).lower()
    explicit_no_image_markers = [
        "link-only",
        "no-image",
        "no image",
        "without images",
        "不要图片",
        "不下载图片",
        "只要链接",
        "仅链接",
        "用户明确要求",
    ]
    explicit_no_image = any(marker in incomplete_reason for marker in explicit_no_image_markers)

    if download_mode == "not_requested" and not explicit_no_image:
        errors.append(
            "download_mode is not_requested. New case packages must handle images by default; "
            "use completed or partial unless the user explicitly asked for link-only/no-image output "
            "and record that request in incomplete_reason."
        )

    if download_mode in {"completed", "partial"} and isinstance(images, list) and not images:
        gap_text = incomplete_reason + " " + json.dumps(
            data.get("uncertain_or_conflicting_info", []),
            ensure_ascii=False,
        ).lower()
        image_gap_markers = [
            "no reliable image",
            "no reliable drawing",
            "未找到可靠图片",
            "未检索到可靠图片",
            "未找到可靠图纸",
            "未检索到可靠图纸",
            "图片来源不足",
            "图纸来源不足",
        ]
        if not any(marker in gap_text for marker in image_gap_markers):
            errors.append(
                "download_mode indicates image handling, but image_metadata is empty. "
                "Download at least one analysis-relevant image/drawing, record failed/skipped image sources, "
                "or explain the lack of reliable image sources in incomplete_reason and uncertain_or_conflicting_info."
            )

    if download_mode == "completed" and isinstance(images, list):
        not_downloaded = [
            str(image.get("id", index))
            for index, image in enumerate(images)
            if isinstance(image, dict) and image.get("download_status") != "downloaded"
        ]
        if not_downloaded:
            errors.append(
                "download_mode is completed, but these images are not marked downloaded: "
                + ", ".join(not_downloaded)
            )


def validate_markdown_image_usage(
    value: Any,
    download_mode: Any,
    md_text: str,
    folder: Path,
    errors: list[str],
    warnings: list[str],
    strong_warnings: list[str],
) -> None:
    if not isinstance(value, list):
        return

    placeholder_pattern = re.compile(r"相关(?:图片|图纸|图片\s*/\s*图纸)[^。\n|]*img\d+", re.IGNORECASE)
    for match in placeholder_pattern.finditer(md_text):
        errors.append(
            "case.md uses image-id placeholders instead of embedded images or source links near the analysis: "
            + match.group(0)[:80]
        )

    direct_image_url_pattern = re.compile(r"https?://[^\s)\]|]+?\.(?:jpe?g|png|gif|webp)(?:\?[^\s)\]|]*)?", re.IGNORECASE)
    for line_number, line in enumerate(md_text.splitlines(), start=1):
        if line.lstrip().startswith("|") and direct_image_url_pattern.search(line) and "](" not in line:
            strong_warnings.append(
                f"case.md line {line_number} has a raw image URL in a table; embed downloaded images in the body or explain failed/skipped status near the analysis."
            )

    for index, image in enumerate(value):
        if not isinstance(image, dict):
            continue

        image_id = str(image.get("id", f"image_metadata[{index}]"))
        status = image.get("download_status")
        source_url = str(image.get("source_url", "")).strip()
        file_name = str(image.get("file_name", "")).strip().replace("\\", "/")

        if status == "downloaded":
            if not file_name:
                continue

            local_path = folder / file_name
            if not local_path.exists():
                errors.append(f"{image_id} is marked downloaded but file does not exist: {file_name}")

            image_embed_pattern = re.compile(r"!\[[^\]]*\]\(" + re.escape(file_name) + r"\)")
            if not image_embed_pattern.search(md_text):
                errors.append(
                    f"{image_id} is marked downloaded but case.md does not embed it with Markdown image syntax: {file_name}"
                )

        if status in {"failed", "skipped"}:
            if source_url and source_url not in md_text:
                strong_warnings.append(
                    f"{image_id} is {status} but its source URL does not appear in case.md near the relevant analysis."
                )

    if download_mode in {"completed", "partial"} and "![" not in md_text:
        errors.append("download_mode indicates images were handled, but case.md contains no Markdown image embeds.")


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


def validate_extended_fields(
    data: dict[str, Any],
    source_ids: set[str],
    image_ids: set[str],
    errors: list[str],
    warnings: list[str],
) -> None:
    missing = [key for key in EXTENDED_TOP_LEVEL if key not in data]
    if missing:
        warnings.append(
            "case.json is missing extended concept-to-built fields: "
            + ", ".join(missing)
            + ". Legacy packages may omit them, but new packages should include them."
        )
        return

    validate_technical_metrics(data.get("technical_metrics"), source_ids, image_ids, errors)
    validate_site_information(data.get("site_information"), source_ids, image_ids, errors)
    validate_evidence_note_groups(
        data.get("conceptual_exploration"),
        "conceptual_exploration",
        ["diagnosis", "positioning", "strategy", "imagery_and_expression"],
        source_ids,
        image_ids,
        errors,
    )
    validate_evidence_note_groups(
        data.get("architectural_language_generation"),
        "architectural_language_generation",
        ["function", "layout", "composition", "place_atmosphere"],
        source_ids,
        image_ids,
        errors,
    )
    validate_evidence_note_groups(
        data.get("construction_quality_control"),
        "construction_quality_control",
        ["construction_language", "materials_and_craft", "tectonic_logic", "performance_and_construction_control"],
        source_ids,
        image_ids,
        errors,
    )
    validate_design_lessons(data.get("design_lessons"), source_ids, image_ids, errors)


def validate_technical_metrics(value: Any, source_ids: set[str], image_ids: set[str], errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append("'technical_metrics' must be an object")
        return
    metric_keys = [
        "site_area",
        "building_area",
        "height",
        "floors",
        "far",
        "building_density",
        "structure_system",
        "client",
    ]
    required = metric_keys + ["main_materials", "photography_drawing_credits", "notes"]
    require_keys(value, required, "technical_metrics", errors)
    for key in metric_keys:
        if key in value:
            validate_metric_value(value.get(key), f"technical_metrics.{key}", source_ids, errors)
    for key in ["main_materials", "photography_drawing_credits"]:
        if key in value:
            validate_evidence_note_list(value.get(key), f"technical_metrics.{key}", source_ids, image_ids, errors)
    if "notes" in value and not isinstance(value["notes"], str):
        errors.append("technical_metrics.notes must be a string")


def validate_metric_value(value: Any, label: str, source_ids: set[str], errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return
    require_keys(value, ["value", "unit", "confidence", "source_ids", "notes"], label, errors)
    if "unit" in value and not isinstance(value["unit"], str):
        errors.append(f"{label}.unit must be a string")
    if value.get("confidence") not in METRIC_CONFIDENCE_VALUES:
        errors.append(f"{label}.confidence must be one of {sorted(METRIC_CONFIDENCE_VALUES)}")
    if "notes" in value and not isinstance(value["notes"], str):
        errors.append(f"{label}.notes must be a string")
    validate_source_refs(value.get("source_ids"), source_ids, label, errors)


def validate_site_information(value: Any, source_ids: set[str], image_ids: set[str], errors: list[str]) -> None:
    validate_evidence_note_groups(
        value,
        "site_information",
        [
            "location_role",
            "natural_environment",
            "cultural_environment",
            "terrain_conditions",
            "roads_and_access",
            "surrounding_buildings",
            "served_users",
            "core_site_tension",
        ],
        source_ids,
        image_ids,
        errors,
        values_are_lists=False,
    )


def validate_design_lessons(value: Any, source_ids: set[str], image_ids: set[str], errors: list[str]) -> None:
    if not isinstance(value, dict):
        errors.append("'design_lessons' must be an object")
        return
    require_keys(value, ["transferable_methods", "avoid_copying", "analysis_diagram_potential"], "design_lessons", errors)
    validate_evidence_note_list(
        value.get("transferable_methods"),
        "design_lessons.transferable_methods",
        source_ids,
        image_ids,
        errors,
    )
    validate_evidence_note_list(
        value.get("avoid_copying"),
        "design_lessons.avoid_copying",
        source_ids,
        image_ids,
        errors,
    )
    diagrams = value.get("analysis_diagram_potential")
    if not isinstance(diagrams, list):
        errors.append("design_lessons.analysis_diagram_potential must be an array")
    else:
        for index, item in enumerate(diagrams):
            if not isinstance(item, str):
                errors.append(f"design_lessons.analysis_diagram_potential[{index}] must be a string")


def validate_evidence_note_groups(
    value: Any,
    label: str,
    keys: list[str],
    source_ids: set[str],
    image_ids: set[str],
    errors: list[str],
    values_are_lists: bool = True,
) -> None:
    if not isinstance(value, dict):
        errors.append(f"'{label}' must be an object")
        return
    require_keys(value, keys, label, errors)
    for key in keys:
        if key not in value:
            continue
        item_label = f"{label}.{key}"
        if values_are_lists:
            validate_evidence_note_list(value.get(key), item_label, source_ids, image_ids, errors)
        else:
            validate_evidence_note(value.get(key), item_label, source_ids, image_ids, errors)


def validate_evidence_note_list(
    value: Any,
    label: str,
    source_ids: set[str],
    image_ids: set[str],
    errors: list[str],
) -> None:
    if not isinstance(value, list):
        errors.append(f"{label} must be an array")
        return
    for index, item in enumerate(value):
        validate_evidence_note(item, f"{label}[{index}]", source_ids, image_ids, errors)


def validate_evidence_note(
    value: Any,
    label: str,
    source_ids: set[str],
    image_ids: set[str],
    errors: list[str],
) -> None:
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return
    require_keys(value, ["text", "evidence_type", "source_ids", "related_image_ids"], label, errors)
    if "text" in value and not isinstance(value["text"], str):
        errors.append(f"{label}.text must be a string")
    if value.get("evidence_type") not in EVIDENCE_TYPES:
        errors.append(f"{label}.evidence_type must be one of {sorted(EVIDENCE_TYPES)}")
    validate_source_refs(value.get("source_ids"), source_ids, label, errors)
    validate_image_refs(value.get("related_image_ids"), image_ids, label, errors)


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
