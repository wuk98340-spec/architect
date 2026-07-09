#!/usr/bin/env python3
"""Score architecture case-package writing against a benchmark-derived review rubric."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CASE_ROOT = ROOT.parent / "case-packages"
VALIDATOR = ROOT / "skills" / "architectural-case-study" / "scripts" / "validate_case_package.py"
BENCHMARK_SLUGS = [
    "guangzhou-jiefang-middle-road-old-city-renewal",
    "taizhou-folk-culture-exhibition-center",
    "shanghai-expo-china-pavilion",
    "suzhou-museum-new",
]

REQUIRED_EXTENDED = [
    "technical_metrics",
    "site_information",
    "conceptual_exploration",
    "architectural_language_generation",
    "construction_quality_control",
    "design_lessons",
]
ANALYSIS_COVERAGE = {
    "concept",
    "context",
    "program",
    "circulation",
    "facade_material",
    "structure_construction",
    "user_experience",
    "urban_relationship",
}
CORE_IMAGE_TYPES = {"02_site", "03_plan", "04_section", "05_elevation", "06_detail", "07_concept", "09_analysis"}
VAGUE_TERMS = [
    "值得学习",
    "很有启发",
    "丰富空间",
    "提升品质",
    "文化表达",
    "现代感",
    "地域特色",
]


@dataclass
class SectionScore:
    name: str
    score: float
    maximum: float
    notes: list[str] = field(default_factory=list)


@dataclass
class ReviewResult:
    slug: str
    path: Path
    score: float
    grade: str
    sections: list[SectionScore]
    blocking_issues: list[str]
    review_focus: list[str]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "cases",
        nargs="*",
        help="Case package folders or slugs. Defaults to all case-packages/* with case.json.",
    )
    parser.add_argument(
        "--benchmarks",
        action="store_true",
        help="Score the four PDF benchmark cases used to calibrate this rubric.",
    )
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--output", type=Path, help="Write the report to this path.")
    parser.add_argument(
        "--skip-validator",
        action="store_true",
        help="Skip the existing schema/package validator and run only rubric checks.",
    )
    args = parser.parse_args()

    case_paths = resolve_case_paths(args.cases, args.benchmarks)
    if not case_paths:
        print("No case packages found.", file=sys.stderr)
        return 2

    results = [review_case(path, skip_validator=args.skip_validator) for path in case_paths]
    if args.format == "json":
        report = json.dumps([result_to_dict(result) for result in results], ensure_ascii=False, indent=2)
    else:
        report = render_markdown(results, benchmark_mode=args.benchmarks)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report + "\n", encoding="utf-8")
    else:
        print(report)
    return 0


def resolve_case_paths(items: list[str], benchmark_mode: bool) -> list[Path]:
    if benchmark_mode:
        return [CASE_ROOT / slug for slug in BENCHMARK_SLUGS if (CASE_ROOT / slug / "case.json").exists()]
    if items:
        paths = []
        for item in items:
            path = Path(item)
            if not path.exists():
                path = CASE_ROOT / item
            paths.append(path)
        return [path for path in paths if (path / "case.json").exists()]
    return sorted(path for path in CASE_ROOT.iterdir() if (path / "case.json").exists())


def review_case(path: Path, skip_validator: bool = False) -> ReviewResult:
    slug = path.name
    data = read_json(path / "case.json")
    md_text = read_text(path / "case.md")

    blocking_issues: list[str] = []
    review_focus: list[str] = []
    sections: list[SectionScore] = []

    sections.append(score_package_integrity(path, data, md_text, blocking_issues, skip_validator))
    sections.append(score_text_argument_chain(data, md_text, review_focus))
    sections.append(score_strategy_quality(data, md_text, review_focus))
    sections.append(score_evidence_language(data, md_text, review_focus))
    sections.append(score_concept_to_built(data, md_text, review_focus))
    sections.append(score_image_integration(path, data, md_text, review_focus))
    sections.append(score_writing_review_signals(data, md_text, review_focus))

    total = round(sum(section.score for section in sections), 1)
    grade = grade_for_score(total, blocking_issues)
    return ReviewResult(slug, path, total, grade, sections, blocking_issues, dedupe(review_focus))


def score_package_integrity(
    path: Path,
    data: dict[str, Any],
    md_text: str,
    blocking_issues: list[str],
    skip_validator: bool,
) -> SectionScore:
    score = 10.0
    notes: list[str] = []
    if not data:
        return SectionScore("Package integrity", 0, 10, ["case.json is missing or invalid."])
    if not md_text.strip():
        blocking_issues.append("case.md is missing or empty.")
        return SectionScore("Package integrity", 2, 10, ["case.md is missing or empty."])

    if not skip_validator and VALIDATOR.exists():
        result = subprocess.run(
            [sys.executable, str(VALIDATOR), str(path)],
            cwd=str(ROOT),
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            score -= 5
            blocking_issues.append("Existing validator reports blocking package errors.")
            notes.append("Run validate_case_package.py and fix blocking errors first.")
        elif "WARNING:" in result.stdout or "STRONG WARNING:" in result.stdout:
            score -= 1
            notes.append("Validator passed with warnings; review before publishing.")

    if "project_name" not in data or not str(data.get("project_name", "")).strip():
        score -= 1
        notes.append("Missing project_name.")
    if "# " not in md_text[:500]:
        score -= 1
        notes.append("case.md does not start with a clear title.")
    if len(md_text) < 3000:
        score -= 2
        notes.append("case.md is short for a benchmark-level case analysis.")

    return SectionScore("Package integrity", clamp(score, 0, 10), 10, notes)


def score_text_argument_chain(data: dict[str, Any], md_text: str, review_focus: list[str]) -> SectionScore:
    score = 20.0
    notes: list[str] = []

    headings = [
        "一句话",
        "场地",
        "概念",
        "建筑语言",
        "建造",
        "核心方法",
        "启发",
        "缺口",
    ]
    missing_heading_signals = [heading for heading in headings if heading not in md_text]
    if len(missing_heading_signals) >= 4:
        score -= 4
        notes.append("Markdown lacks several benchmark text sections: " + ", ".join(missing_heading_signals[:5]))

    chain_terms = {
        "problem": ["问题", "矛盾", "约束", "挑战", "诊断"],
        "method": ["做法", "策略", "方法", "组织", "转化"],
        "effect": ["效果", "形成", "带来", "使得", "回应"],
        "transfer": ["可迁移", "启发", "方法", "不宜直接照搬"],
    }
    for label, terms in chain_terms.items():
        if not any(term in md_text for term in terms):
            score -= 2
            notes.append(f"Text has weak '{label}' signal in the argument chain.")

    one_sentence = str(data.get("one_sentence_summary", ""))
    if not one_sentence.strip():
        score -= 2
        notes.append("Missing one_sentence_summary.")
    elif len(one_sentence) < 35:
        score -= 1
        notes.append("one_sentence_summary is too thin to anchor the case judgment.")

    if count_occurrences(md_text, ["来源明确", "基于资料", "PDF", "source", "证据"]) < 5:
        score -= 3
        notes.append("Text rarely marks whether claims are sourced or synthesized.")

    review_focus.append("Read the text as an argument: project problem -> design method -> spatial/built result -> transferable lesson.")
    return SectionScore("Text argument chain", clamp(score, 0, 20), 20, notes)


def score_evidence_language(data: dict[str, Any], md_text: str, review_focus: list[str]) -> SectionScore:
    score = 15.0
    notes: list[str] = []
    sources = list_of_dicts(data.get("sources"))
    source_ids = {str(source.get("id")) for source in sources if source.get("id")}
    source_quality = data.get("source_quality") if isinstance(data.get("source_quality"), dict) else {}
    source_mode = data.get("source_mode")
    evidence_spans = list_of_dicts(data.get("evidence_spans"))

    if not sources:
        return SectionScore("Evidence language and source discipline", 0, 15, ["No sources recorded."])
    if not any(source.get("source_level") in {"level_a", "level_b"} for source in sources):
        score -= 2
        notes.append("No Level A/B source; confidence should stay cautious.")
    if source_quality.get("source_sufficiency_status") not in {"sufficient", "partial"}:
        score -= 2
        notes.append("Source sufficiency is not sufficient/partial.")
    coverage = set(source_quality.get("analysis_coverage") or [])
    missing_coverage = sorted(ANALYSIS_COVERAGE - coverage)
    if missing_coverage:
        score -= min(2, len(missing_coverage) * 0.5)
        notes.append("Missing analysis coverage: " + ", ".join(missing_coverage))

    if source_mode in {"pdf", "mixed"}:
        if not evidence_spans:
            score -= 2
            notes.append("PDF/mixed case lacks evidence_spans page evidence.")
        elif len(evidence_spans) < 3:
            score -= 1
            notes.append("PDF/mixed case has thin page evidence.")
        if not re.search(r"PDF\s*p\.|PDF\s*pp\.|#page=", md_text, flags=re.IGNORECASE):
            score -= 1
            notes.append("Markdown lacks visible PDF page evidence near claims.")

    for label, items in [
        ("key_facts", list_of_dicts(data.get("key_facts"))),
        ("key_strategies", list_of_dicts(data.get("key_strategies"))),
    ]:
        if any(not set(item.get("source_ids") or []) & source_ids for item in items):
            score -= 1.5
            notes.append(f"Some {label} items lack valid source references.")
            break

    uncertainties = list_of_dicts(data.get("uncertain_or_conflicting_info"))
    if not uncertainties:
        score -= 1.5
        review_focus.append("Check whether missing metrics, construction details, or conflicts were hidden instead of recorded.")
        notes.append("No uncertainty/conflict notes recorded.")

    if count_occurrences(md_text, ["未检索到可靠资料", "资料不足", "未能确认", "需要复核", "缺少"]) < 2:
        score -= 1.5
        notes.append("Missing-information language is weak or absent.")

    review_focus.append("Check whether textual claims distinguish facts, synthesis, and missing evidence.")
    return SectionScore("Evidence language and source discipline", clamp(score, 0, 15), 15, notes)


def score_concept_to_built(data: dict[str, Any], md_text: str, review_focus: list[str]) -> SectionScore:
    score = 15.0
    notes: list[str] = []
    missing = [key for key in REQUIRED_EXTENDED if key not in data]
    if missing:
        score -= min(8, len(missing) * 2)
        notes.append("Missing extended fields: " + ", ".join(missing))

    for key, fields in [
        ("conceptual_exploration", ["diagnosis", "positioning", "strategy", "imagery_and_expression"]),
        ("architectural_language_generation", ["function", "layout", "composition", "place_atmosphere"]),
        ("construction_quality_control", [
            "construction_language",
            "materials_and_craft",
            "tectonic_logic",
            "performance_and_construction_control",
        ]),
    ]:
        section = data.get(key) if isinstance(data.get(key), dict) else {}
        empty_fields = [field for field in fields if not list_of_dicts(section.get(field))]
        if empty_fields:
            score -= min(2.5, len(empty_fields) * 0.7)
            notes.append(f"{key} has empty fields: " + ", ".join(empty_fields))

    if not data.get("technical_metrics"):
        score -= 1
        notes.append("No technical_metrics field.")
    if not data.get("site_information"):
        score -= 1
        notes.append("No site_information field.")

    if "建造品质" not in md_text and "Construction Quality" not in md_text and "构造" not in md_text:
        score -= 2
        notes.append("Text has weak construction/material quality discussion.")

    review_focus.append("Read the three-layer chain: diagnosis/positioning -> spatial language -> construction/material quality.")
    return SectionScore("Concept-to-built coverage", clamp(score, 0, 15), 15, notes)


def score_strategy_quality(data: dict[str, Any], md_text: str, review_focus: list[str]) -> SectionScore:
    score = 20.0
    notes: list[str] = []
    strategies = list_of_dicts(data.get("key_strategies"))

    if len(strategies) < 3 or len(strategies) > 5:
        score -= 5
        notes.append("Benchmark cases use 3-5 key strategies.")
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
    for index, strategy in enumerate(strategies):
        missing = [key for key in required if not strategy.get(key)]
        if missing:
            score -= 1.5
            notes.append(f"Strategy {index + 1} missing/empty: " + ", ".join(missing))
        text_bundle = " ".join(str(strategy.get(key, "")) for key in required)
        if len(text_bundle) < 180:
            score -= 1
            notes.append(f"Strategy {index + 1} is too thin for benchmark quality.")
        if not strategy.get("related_image_ids"):
            score -= 0.5
            notes.append(f"Strategy {index + 1} has no related image/drawing.")
        if has_many_vague_terms(text_bundle):
            score -= 1
            notes.append(f"Strategy {index + 1} may be too generic; manually review depth.")

    lessons = data.get("design_lessons") if isinstance(data.get("design_lessons"), dict) else {}
    if len(list_of_dicts(lessons.get("transferable_methods"))) < 3:
        score -= 2
        notes.append("Fewer than 3 transferable design lessons.")

    if "面对的问题" not in md_text and "设计问题" not in md_text:
        score -= 1.5
        notes.append("Markdown strategy section does not visibly foreground design problems.")
    if "可迁移" not in md_text:
        score -= 1.5
        notes.append("Markdown lacks visible transferable-method language.")

    review_focus.append("For each strategy, judge whether it follows problem -> method -> architectural effect -> evidence -> transferable lesson.")
    return SectionScore("Strategy and transferability", clamp(score, 0, 20), 20, notes)


def score_image_integration(path: Path, data: dict[str, Any], md_text: str, review_focus: list[str]) -> SectionScore:
    score = 5.0
    notes: list[str] = []
    images = list_of_dicts(data.get("image_metadata"))
    image_types = {image.get("image_type") for image in images}
    downloaded = [image for image in images if image.get("download_status") == "downloaded"]

    if data.get("download_mode") not in {"completed", "partial"}:
        score -= 1
        notes.append("download_mode should be completed or partial for current packages.")
    if not images:
        return SectionScore("Image and drawing integration", 0, 5, ["No image_metadata recorded."])
    if len(images) < 3:
        score -= 1
        notes.append("Benchmark cases normally include at least 3 analysis images/drawings.")
    if not (CORE_IMAGE_TYPES & image_types):
        score -= 1
        notes.append("No site/plan/section/detail/concept/analysis drawing type recorded.")
    if not downloaded:
        score -= 1
        notes.append("No downloaded images.")

    for image in images:
        file_name = str(image.get("file_name") or "").replace("\\", "/")
        if image.get("download_status") == "downloaded":
            if file_name and not (path / file_name).exists():
                score -= 0.5
                notes.append(f"Downloaded image missing on disk: {file_name}")
            if file_name and f"]({file_name})" not in md_text:
                score -= 0.5
                notes.append(f"Downloaded image not embedded in case.md: {file_name}")
        if not str(image.get("relevance_reason", "")).strip():
            score -= 0.25
            notes.append(f"Image lacks relevance_reason: {image.get('id', '<unknown>')}")

    review_focus.append("Check whether images prove an analysis claim, not merely decorate the case.")
    return SectionScore("Image and drawing integration", clamp(score, 0, 5), 5, notes[:8])


def score_writing_review_signals(data: dict[str, Any], md_text: str, review_focus: list[str]) -> SectionScore:
    score = 15.0
    notes: list[str] = []

    if not str(data.get("one_sentence_summary", "")).strip():
        score -= 1.5
        notes.append("Missing one_sentence_summary.")
    if data.get("information_confidence") in {"limited", "low"} and not str(data.get("incomplete_reason", "")).strip():
        score -= 1.5
        notes.append("Low/limited confidence lacks incomplete_reason.")
    if "未检索到可靠资料" not in md_text and "PDF" not in md_text and not list_of_dicts(data.get("uncertain_or_conflicting_info")):
        score -= 1.5
        notes.append("No visible evidence of missing-information discipline.")
    vague_hits = [term for term in VAGUE_TERMS if term in md_text]
    if len(vague_hits) >= 4:
        score -= 2
        notes.append("Many generic phrases detected; review for shallow writing.")
    if re.search(r"img\d+|图片\d+|相关图片[:：]\s*$", md_text, flags=re.IGNORECASE | re.MULTILINE):
        score -= 2
        notes.append("Possible image placeholders remain in Markdown.")

    paragraphs = [line.strip() for line in md_text.splitlines() if line.strip() and not line.startswith(("#", "|", "-", "!", ">"))]
    long_generic = [p for p in paragraphs if len(p) > 220 and has_many_vague_terms(p)]
    if long_generic:
        score -= min(2, len(long_generic))
        notes.append("Some long paragraphs appear generic; manually tighten architectural judgment.")

    if count_occurrences(md_text, ["平面", "剖面", "流线", "体量", "立面", "材料", "构造", "节点", "场地"]) < 8:
        score -= 2
        notes.append("Text may lack enough concrete architectural vocabulary.")

    review_focus.append("Manually judge whether the writing avoids promotional summary and stays close to architectural evidence.")
    return SectionScore("Writing depth and precision", clamp(score, 0, 15), 15, notes)


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def clamp(value: float, low: float, high: float) -> float:
    return round(max(low, min(high, value)), 1)


def dedupe(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def count_occurrences(text: str, terms: list[str]) -> int:
    return sum(text.count(term) for term in terms)


def has_many_vague_terms(text: str) -> bool:
    return sum(1 for term in VAGUE_TERMS if term in text) >= 3


def grade_for_score(score: float, blocking_issues: list[str]) -> str:
    if blocking_issues:
        return "BLOCKED"
    if score >= 90:
        return "A benchmark-level"
    if score >= 80:
        return "B publishable with minor review"
    if score >= 70:
        return "C needs revision"
    return "D regenerate or major repair"


def render_markdown(results: list[ReviewResult], benchmark_mode: bool) -> str:
    title = "Benchmark Quality Calibration Report" if benchmark_mode else "Case Quality Review Report"
    lines = [f"# {title}", ""]
    lines.append("| Case | Score | Grade | Main review focus |")
    lines.append("| --- | ---: | --- | --- |")
    for result in results:
        focus = "; ".join(result.review_focus[:2]) or "No manual focus generated."
        lines.append(f"| `{result.slug}` | {result.score:.1f} | {result.grade} | {focus} |")
    lines.append("")

    for result in results:
        lines.extend([f"## {result.slug}", "", f"Score: **{result.score:.1f}/100**  ", f"Grade: **{result.grade}**", ""])
        if result.blocking_issues:
            lines.append("Blocking issues:")
            for issue in result.blocking_issues:
                lines.append(f"- {issue}")
            lines.append("")
        lines.append("| Dimension | Score | Notes |")
        lines.append("| --- | ---: | --- |")
        for section in result.sections:
            notes = "<br>".join(section.notes) if section.notes else "OK"
            lines.append(f"| {section.name} | {section.score:.1f}/{section.maximum:.0f} | {notes} |")
        lines.append("")
        if result.review_focus:
            lines.append("Manual review prompts:")
            for prompt in result.review_focus:
                lines.append(f"- {prompt}")
            lines.append("")
    return "\n".join(lines).rstrip()


def result_to_dict(result: ReviewResult) -> dict[str, Any]:
    return {
        "slug": result.slug,
        "path": str(result.path),
        "score": result.score,
        "grade": result.grade,
        "blocking_issues": result.blocking_issues,
        "review_focus": result.review_focus,
        "sections": [
            {
                "name": section.name,
                "score": section.score,
                "maximum": section.maximum,
                "notes": section.notes,
            }
            for section in result.sections
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main())
