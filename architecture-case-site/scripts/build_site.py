#!/usr/bin/env python3
"""Build a V0 static architecture case research website."""

from __future__ import annotations

import html
import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any

PIPELINE_DIR = Path(__file__).resolve().parents[2] / "ARCHITECT_skill" / "scripts"
if str(PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(PIPELINE_DIR))


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config.example.json"
LOCAL_CONFIG = ROOT / "config.local.json"
SOURCE_DIR = ROOT / "src"
TEMPLATE_DIR = SOURCE_DIR / "templates"
CASE_ROOT = Path()
SITE_ROOT = Path()
ASSET_DIR = Path()
CASE_SITE_DIR = Path()
FEATURED_SLUGS: list[str] = []
API_BASE = ""


def main() -> int:
    configure_paths(load_config())
    cases = load_cases()
    if not cases:
        raise SystemExit("No cases found.")

    if SITE_ROOT.exists():
        try:
            shutil.rmtree(SITE_ROOT)
        except PermissionError:
            pass
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    CASE_SITE_DIR.mkdir(parents=True, exist_ok=True)

    write_assets()
    for case in cases:
        build_case_page(case)
    write_index(cases)
    write_preview()
    strip_generated_trailing_whitespace()
    return 0


def load_config() -> dict[str, Any]:
    parser = argparse.ArgumentParser(description="Build the static architecture case website.")
    parser.add_argument(
        "--config",
        type=Path,
        default=LOCAL_CONFIG if LOCAL_CONFIG.exists() else DEFAULT_CONFIG,
        help="Path to a JSON config file. Defaults to config.local.json when present, otherwise config.example.json.",
    )
    args = parser.parse_args()
    config_path = args.config if args.config.is_absolute() else ROOT / args.config
    if not config_path.exists():
        raise SystemExit(f"Config file not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as handle:
        config = json.load(handle)
    config["_config_path"] = str(config_path)
    return config


def configure_paths(config: dict[str, Any]) -> None:
    global CASE_ROOT, SITE_ROOT, ASSET_DIR, CASE_SITE_DIR, FEATURED_SLUGS, API_BASE
    config_dir = Path(str(config["_config_path"])).parent
    case_packages_dir = Path(os.environ.get("ARCHITECT_CASE_PACKAGES_ROOT", str(config.get("casePackagesDir") or "")))
    output_dir = Path(os.environ.get("ARCHITECT_STATIC_ROOT", str(config.get("outputDir") or "public")))
    CASE_ROOT = case_packages_dir if case_packages_dir.is_absolute() else config_dir / case_packages_dir
    SITE_ROOT = output_dir if output_dir.is_absolute() else config_dir / output_dir
    ASSET_DIR = SITE_ROOT / "assets"
    CASE_SITE_DIR = SITE_ROOT / "cases"
    FEATURED_SLUGS = [str(slug) for slug in config.get("featuredSlugs", []) if str(slug).strip()]
    API_BASE = str(os.environ.get("ARCHITECT_API_BASE", config.get("apiBase") or "")).strip().rstrip("/")
    if not CASE_ROOT.exists():
        raise SystemExit(f"casePackagesDir does not exist: {CASE_ROOT}")


def load_cases() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for json_path in sorted(CASE_ROOT.rglob("case.json")):
        if "revisions" in json_path.parts:
            continue
        md_path = json_path.with_name("case.md")
        if not md_path.exists():
            continue
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue

        folder = json_path.parent
        slug = folder.name
        title = clean(data.get("project_name")) or slug
        architects = normalize_list(data.get("architects"))
        year_text = clean(data.get("year")) or "Unknown year"
        case_type = clean(data.get("case_type") or data.get("program")) or "Uncategorized"
        location = clean(data.get("location")) or "Unknown location"
        summary = clean(data.get("one_sentence_summary")) or first_markdown_paragraph(md_path)
        gallery = image_items(data, folder)
        cover = pick_cover(gallery)
        strategies = list_of_dicts(data.get("key_strategies"))
        keywords = build_keywords(data, case_type, strategies)

        items.append(
            {
                "slug": slug,
                "folder": folder,
                "md_path": md_path,
                "data": data,
                "title": title,
                "architects": architects,
                "architects_text": " / ".join(architects) if architects else "Unknown architect",
                "location": location,
                "region": infer_region(location),
                "year_text": year_text,
                "sort_year": extract_sort_year(year_text),
                "type": case_type,
                "program": clean(data.get("program")),
                "status": clean(data.get("status")),
                "summary": summary,
                "confidence": clean(data.get("information_confidence")) or "unknown",
                "area": extract_area(data),
                "cover": cover,
                "gallery": gallery,
                "keywords": keywords,
                "strategies": strategies,
                "spatial": list_of_dicts(data.get("spatial_ideas")),
                "site": list_of_dicts(data.get("site_context")),
                "materials": list_of_dicts(data.get("materials_structure")),
                "sources": list_of_dicts(data.get("sources")),
                "warnings": list_of_dicts(data.get("uncertain_or_conflicting_info")),
                "source_count": len(list_of_dicts(data.get("sources"))),
                "image_count": len(gallery),
                "search_blob": "",
            }
        )

    for item in items:
        item["search_blob"] = " ".join(
            [
                item["title"],
                item["architects_text"],
                item["location"],
                item["region"],
                item["year_text"],
                item["type"],
                item["program"],
                item["summary"],
                " ".join(item["keywords"]),
                " ".join(clean(s.get("strategy_name")) + " " + clean(s.get("specific_approach")) for s in item["strategies"]),
            ]
        ).lower()

    # The case page is a research reader rather than a thumbnail gallery. Keep
    # all local evidence assets here; placement and per-page uniqueness are
    # governed later by their Markdown context and related_sections metadata.

    return sorted(items, key=lambda c: (c["sort_year"] or 0, c["title"]), reverse=True)


def build_case_page(case: dict[str, Any]) -> None:
    out_dir = CASE_SITE_DIR / case["slug"]
    out_dir.mkdir(parents=True, exist_ok=True)
    image_dir = case["folder"] / "images"
    if image_dir.exists():
        shutil.copytree(image_dir, out_dir / "images", dirs_exist_ok=True)

    slides = build_case_deck_slides(case)
    slides_html = "".join(slide["html"] for slide in slides)

    body = f"""
    <header class="site-header detail-header">
      <a class="brand" href="../../index.html"><span>ARCHIVE</span><strong>建筑案例研究</strong></a>
      <nav><a href="../../index.html#cases">返回案例库</a></nav>
    </header>
    <main class="detail case-deck" data-case-deck>
      <section class="deck-stage" aria-live="polite">
        {slides_html}
      </section>
      <footer class="deck-controls">
        <button class="deck-arrow" type="button" data-slide-prev aria-label="上一页">&lsaquo;</button>
        <div class="deck-status" aria-live="polite">
          <strong data-slide-label-current></strong>
          <span><b data-slide-index>01</b> / <b data-slide-count>{len(slides):02d}</b></span>
        </div>
        <button class="deck-arrow" type="button" data-slide-next aria-label="下一页">&rsaquo;</button>
      </footer>
    </main>
    """
    (out_dir / "index.html").write_text(page_shell(case["title"], body, 2), encoding="utf-8")



def build_case_deck_slides(case: dict[str, Any]) -> list[dict[str, str]]:
    # Images are evidence, not decoration: a non-cover asset can appear once,
    # while the cover asset may appear once more when it is embedded beside the
    # chapter it actually supports.
    case["_slide_image_uses"] = {}
    chunks = markdown_deck_chunks(Path(case["md_path"]))
    slides: list[dict[str, str]] = []

    def add(label: str, title: str, body: str, media: str = "", variant: str = "") -> None:
        if not body.strip() and not media.strip():
            return
        number = f"{len(slides) + 1:02d}"
        class_name = "deck-slide" + (f" {variant}" if variant else "")
        primary_title, secondary_title = split_strategy_heading(title)
        heading_html = f"<h1>{esc(primary_title)}</h1>"
        media_block = f"\n                    {media}" if media else ""
        if secondary_title:
            heading_html += f'<h2 class="slide-subtitle">{esc(secondary_title)}</h2>'
        slides.append(
            {
                "label": label,
                "html": f"""
                <article class="{class_name}" data-slide data-slide-label="{esc(label)}" data-screen-label="{number} {esc(label)}">
                  <div class="slide-grid">
                    <div class="slide-copy">
                      <p class="section-number">{number}</p>
                      {heading_html}
                      {body}
                    </div>{media_block}
                  </div>
                </article>
                """,
            }
        )

    add(
        "封面",
        case["title"],
        f'<p class="slide-lead">{esc(case["summary"])}</p><div class="detail-tags">{tag_html(case["keywords"][:2])}</div>',
        render_slide_media(case, 0, hero=True),
        "is-cover",
    )

    for index, chunk in enumerate(chunks, 1):
        if should_skip_markdown_chunk(chunk["title"]):
            continue
        text_only = is_text_only_slide(chunk["title"])
        information_page = is_information_slide(chunk["title"])
        body, media, has_table = render_markdown_slide_content(
            case,
            chunk["lines"],
            chunk["title"],
            index,
            text_only,
            prefer_table=information_page,
        )
        variants = []
        content_length = len("".join(chunk["lines"]))
        if has_table or content_length > 420:
            variants.append("is-dense")
        if content_length > 750:
            variants.append("is-compact")
        if text_only:
            variants.append("is-text-only")
        if information_page:
            variants.append("is-information-page")
        if is_basic_info_slide(chunk["title"]):
            variants.append("is-basic-info")
        if "is-transposed" in body:
            variants.append("has-wide-table")
        add(
            chunk["label"],
            display_slide_title(chunk["title"]),
            body,
            media,
            " ".join(variants),
        )

    compact_sources = render_compact_sources(case["sources"])
    if compact_sources:
        add("Sources", "Reference Sources", compact_sources, "", "is-appendix is-text-only")

    return slides


def markdown_deck_chunks(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    chunks: list[dict[str, Any]] = []
    current_h2 = ""
    current_lines: list[str] = []
    current_title = ""
    current_label = ""

    def flush() -> None:
        nonlocal current_lines, current_title, current_label
        if current_title and any(line.strip() for line in current_lines):
            chunks.append({"label": current_label or current_title, "title": current_title, "lines": current_lines})
        current_lines = []

    for line in lines:
        if line.startswith("# "):
            continue
        if line.startswith("## "):
            flush()
            current_h2 = line[3:].strip()
            current_title = current_h2
            current_label = compact_slide_label(current_h2)
            continue
        if line.startswith("### "):
            flush()
            subtitle = line[4:].strip()
            current_title = subtitle
            current_label = compact_slide_label(subtitle or current_h2)
            continue
        if current_title:
            current_lines.append(line)

    flush()
    return chunks


def compact_slide_label(title: str) -> str:
    title = re.sub(r"^\d+(?:\.\d+)?\s*", "", title).strip()
    title = re.sub(r"\s+[A-Za-z][A-Za-z &/,-]*$", "", title).strip()
    return short(title, 10)


def display_slide_title(title: str) -> str:
    title = re.sub(r"^\d+(?:\.\d+)?\s*", "", title).strip()
    title = re.sub(r"\s+[A-Za-z][A-Za-z &/,-]*$", "", title).strip()
    if is_basic_info_slide(title):
        return "基本信息"
    return title


def split_strategy_heading(title: str) -> tuple[str, str]:
    """Split strategy number and description into two readable heading levels."""
    match = re.match(r"^(策略\s*[0-9一二三四五六七八九十]+)\s*[:：]\s*(.+)$", clean(title), flags=re.IGNORECASE)
    if not match:
        return title, ""
    primary = match.group(1).replace("策略", "策略 ", 1)
    return re.sub(r"\s+", " ", primary).strip(), match.group(2).strip()


def is_basic_info_slide(title: str) -> bool:
    normalized = re.sub(r"\s+", "", title).lower()
    return "基本信息" in normalized or "经济技术指标" in normalized or "basicinfo" in normalized


def is_information_slide(title: str) -> bool:
    normalized = re.sub(r"\s+", "", title).lower()
    keywords = ["基本信息", "经济技术指标", "技术指标", "场地信息表", "场地信息", "basicinfo", "siteinformation", "metrics"]
    return any(keyword in normalized for keyword in keywords)


def should_skip_markdown_chunk(title: str) -> bool:
    normalized = re.sub(r"\s+", "", title).lower()
    skip_keywords = [
        "sourcequality",
        "evidence",
        "imageindex",
        "informationgap",
        "conflict",
        "sourcelist",
        "levela",
        "levelb",
        "levelc",
        "leveld",
        "图纸与图片索引",
        "图片索引",
        "补充图片证据",
    ]
    return any(keyword.lower() in normalized for keyword in skip_keywords)


def is_text_only_slide(title: str) -> bool:
    normalized = re.sub(r"\s+", "", title).lower()
    text_only_keywords = [
        "基本信息",
        "经济技术指标",
        "技术指标",
        "场地信息表",
        "场地信息",
        "basic",
        "info",
        "metrics",
        "site",
        "参考资料",
        "来源",
        "source",
    ]
    return any(keyword.lower() in normalized for keyword in text_only_keywords)


def is_source_note_label(value: str) -> bool:
    normalized = clean(value).strip(":： ").lower()
    return normalized in {"source", "sources", "evidence", "reference", "references"}


def render_compact_sources(sources: list[dict[str, Any]]) -> str:
    if not sources:
        return ""
    items = []
    for source in sources[:5]:
        title = clean(source.get("title")) or clean(source.get("url"))
        url = clean(source.get("url"))
        publisher = clean(source.get("publisher"))
        if not title:
            continue
        link = f'<a href="{esc(url)}">{esc(title)}</a>' if url else esc(title)
        meta = f'<span>{esc(publisher)}</span>' if publisher else ""
        items.append(f"<li>{link}{meta}</li>")
    if not items:
        return ""
    return '<ul class="compact-source-list">' + "".join(items) + "</ul>"


def render_markdown_slide_content(
    case: dict[str, Any],
    lines: list[str],
    title: str,
    fallback_index: int,
    text_only: bool = False,
    prefer_table: bool = False,
) -> tuple[str, str, bool]:
    image_lines, remaining = extract_markdown_images(lines)
    media = "" if text_only else render_markdown_image_media_group(case, image_lines, title)
    body, has_table = render_markdown_fragment(remaining, prefer_table=prefer_table)
    return body, media, has_table


def is_generic_image_gallery(title: str) -> bool:
    normalized = normalize_section_name(title)
    return normalized in {"案例图像", "项目图像", "项目照片", "图像"}


def extract_markdown_images(lines: list[str]) -> tuple[list[str], list[str]]:
    image_lines: list[str] = []
    remaining: list[str] = []
    for line in lines:
        if re.match(r"\s*!\[[^\]]*\]\([^)]+\)", line):
            image_lines.append(line)
        else:
            remaining.append(line)
    return image_lines, remaining


def render_markdown_image_media_group(case: dict[str, Any], lines: list[str], title: str) -> str:
    images: list[dict[str, Any]] = []
    for line in lines:
        match = re.match(r"\s*!\[([^\]]*)\]\(([^)]+)\)", line)
        if not match:
            continue
        file_name = Path(clean(match.group(2))).name
        image = next(
            (candidate for candidate in case["gallery"] if Path(clean(candidate.get("src"))).name == file_name),
            None,
        )
        if not image or not image_available(case, image):
            continue
        # A generic image overview should add evidence, not repeat the cover as
        # its first tile. The cover remains reusable in analytical sections.
        if is_generic_image_gallery(title) and image_key(image) == image_key(case.get("cover") or {}):
            continue
        images.append(image)

    # Images grouped under a supplemental-evidence heading are not rendered in
    # that catch-all section. Their JSON related_sections metadata lets us place
    # them beside the chapter where the claim is made instead.
    images.extend(related_supplemental_images(case, title))
    return render_slide_media_group(case, images)


def image_key(image: dict[str, Any]) -> str:
    return clean(image.get("id")) or clean(image.get("src"))


def image_use_limit(case: dict[str, Any], image: dict[str, Any]) -> int:
    cover = case.get("cover") or {}
    return 2 if image_key(image) and image_key(image) == image_key(cover) else 1


def image_available(case: dict[str, Any], image: dict[str, Any]) -> bool:
    key = image_key(image)
    return bool(key) and case.setdefault("_slide_image_uses", {}).get(key, 0) < image_use_limit(case, image)


def register_image_use(case: dict[str, Any], image: dict[str, Any]) -> None:
    key = image_key(image)
    uses = case.setdefault("_slide_image_uses", {})
    uses[key] = uses.get(key, 0) + 1


def normalize_section_name(value: str) -> str:
    value = re.sub(r"^\d+(?:\.\d+)?\s*", "", clean(value))
    value = re.sub(r"\s+[A-Za-z][A-Za-z &/,-]*$", "", value)
    return re.sub(r"[\s：:，,、/（）()\-—]", "", value).lower()


def related_section_terms(title: str) -> set[str]:
    normalized = normalize_section_name(title)
    terms = {normalized}
    aliases = {
        "一句话判断": {"项目定位与核心判断"},
        "诊断": {"项目定位与核心判断"},
        "定位": {"项目定位与核心判断"},
        "场地信息表": {"场地与城市关系"},
        "功能梳理": {"功能与使用逻辑"},
        "布局逻辑": {"布局逻辑"},
        "形式构成": {"形式构成"},
        "场所与氛围": {"场所与氛围", "城市界面"},
        "意象与表达": {"地方文化转译"},
        "建造语言": {"建造语言"},
        "材料与工艺": {"材料与工艺"},
        "构造逻辑": {"构造逻辑"},
    }
    for key, values in aliases.items():
        if key in normalized:
            terms.update(normalize_section_name(value) for value in values)
    return {term for term in terms if term}


def related_supplemental_images(case: dict[str, Any], title: str) -> list[dict[str, Any]]:
    terms = related_section_terms(title)
    matches: list[dict[str, Any]] = []
    for image in case["gallery"]:
        if not image_available(case, image):
            continue
        related = {normalize_section_name(value) for value in image.get("related_sections", []) if clean(value)}
        if not related:
            continue
        if any(term in section or section in term for term in terms for section in related):
            matches.append(image)
    return matches


def render_slide_media_group(case: dict[str, Any], images: list[dict[str, Any]]) -> str:
    unique_images: list[dict[str, Any]] = []
    seen: set[str] = set()
    for image in images:
        key = image_key(image)
        if key and key not in seen and image_available(case, image):
            seen.add(key)
            unique_images.append(image)
    if not unique_images:
        return ""
    figures = []
    for image in unique_images:
        register_image_use(case, image)
        caption = clean(image.get("caption"))
        caption_html = f'<figcaption>{esc(caption)}</figcaption>' if caption else ""
        figures.append(f'<figure class="slide-media">{image_tag(image, "")}{caption_html}</figure>')
    class_name = "slide-media-group media-count-" + str(len(figures))
    if len(figures) > 1:
        class_name += " has-multiple-media"
    return f'<div class="{class_name}">' + "".join(figures) + "</div>"


def render_markdown_fragment(lines: list[str], prefer_table: bool = False) -> tuple[str, bool]:
    html_parts: list[str] = []
    paragraph: list[str] = []
    list_items: list[str] = []
    table_rows: list[str] = []
    has_table = False

    def display_text(text: str) -> str:
        normalized = clean(text).replace("证据不足", "资料不足").replace("参与证据", "参与资料")
        return re.sub(r"\s*\[s\d+\]", "", normalized, flags=re.IGNORECASE).strip()

    def normalize_basic_info_rows(rows: list[list[str]]) -> list[tuple[str, str]]:
        normalized: list[tuple[str, str]] = []
        skip_labels = {"项目名称", "英文名称", "主要依据来源", "证据", "证据来源"}
        for row in rows:
            if len(row) < 2:
                continue
            label = clean(row[0])
            value = clean(row[1])
            if not label or not value:
                continue
            if label in skip_labels or "证据" in label:
                continue
            normalized.append((label, value))
        return normalized

    def render_fact_list(items: list[tuple[str, str]]) -> str:
        rows = "".join(
            f'<li><strong>{esc(display_text(label))}：</strong><span>{esc(display_text(value))}</span></li>'
            for label, value in items
            if clean(label) and clean(value)
        )
        return f'<ul class="fact-list">{rows}</ul>'

    def render_transposed_table(labels: list[str], values: list[str], extra_class: str = "") -> str:
        classes = "data-table transposed-table" + (f" {extra_class}" if extra_class else "")
        thead = "<thead><tr>" + "".join(f"<th>{esc(display_text(cell))}</th>" for cell in labels) + "</tr></thead>"
        tbody = "<tbody><tr>" + "".join(f"<td>{esc(display_text(cell))}</td>" for cell in values) + "</tr></tbody>"
        return f'<div class="table-wrap markdown-table is-transposed"><table class="{classes}">{thead}{tbody}</table></div>'

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            html_parts.append(f'<p>{" ".join(esc(item) for item in paragraph)}</p>')
            paragraph = []

    def flush_list() -> None:
        nonlocal list_items, has_table
        if list_items:
            fact_rows = []
            if prefer_table:
                for item in list_items:
                    match = re.match(r"^([^:：]{1,28})[:：]\s*(.+)$", item)
                    if not match:
                        fact_rows = []
                        break
                    fact_rows.append((match.group(1).strip(), match.group(2).strip()))
            if fact_rows:
                tbody = "".join(
                    f"<tr><th>{esc(display_text(label))}</th><td>{esc(display_text(value))}</td></tr>"
                    for label, value in fact_rows
                )
                html_parts.append(f'<div class="table-wrap markdown-table"><table class="data-table info-table"><tbody>{tbody}</tbody></table></div>')
                has_table = True
            else:
                html_parts.append('<ul class="slide-list">' + "".join(f"<li>{esc(item)}</li>" for item in list_items) + "</ul>")
            list_items = []

    def flush_table() -> None:
        nonlocal table_rows, has_table
        if not table_rows:
            return
        parsed = [[cell.strip() for cell in row.strip().strip("|").split("|")] for row in table_rows]
        if len(parsed) >= 2 and all(re.fullmatch(r":?-{3,}:?", cell) for cell in parsed[1]):
            head = parsed[0]
            body_rows = parsed[2:]
        else:
            head = []
            body_rows = parsed
        body_rows = [
            row
            for row in body_rows
            if not row or not is_source_note_label(row[0])
        ]
        if head:
            evidence_indexes = {index for index, cell in enumerate(head) if "证据" in cell}
            if evidence_indexes:
                head = [cell for index, cell in enumerate(head) if index not in evidence_indexes]
                body_rows = [
                    [cell for index, cell in enumerate(row) if index not in evidence_indexes]
                    for row in body_rows
                ]
        thead = "<thead><tr>" + "".join(f"<th>{esc(display_text(cell))}</th>" for cell in head) + "</tr></thead>" if head else ""
        tbody = "<tbody>" + "".join("<tr>" + "".join(f"<td>{esc(display_text(cell))}</td>" for cell in row) + "</tr>" for row in body_rows) + "</tbody>"
        html_parts.append(f'<div class="table-wrap markdown-table"><table class="data-table">{thead}{tbody}</table></div>')
        has_table = True
        table_rows = []

    for raw in lines:
        line = raw.rstrip()
        presentation_note = line.strip().strip("*_ ")
        if presentation_note.lower().startswith(("image note:", "caption:", "media note:", "图像用途：", "图文相关性：", "图片说明：", "配图说明：")):
            flush_paragraph()
            flush_list()
            continue
        if not line.strip():
            flush_paragraph()
            flush_list()
            flush_table()
            continue
        if line.lstrip().startswith("|"):
            flush_paragraph()
            flush_list()
            table_rows.append(line)
            continue
        flush_table()
        if line.startswith(">"):
            flush_paragraph()
            flush_list()
            html_parts.append(f'<blockquote>{esc(display_text(line.lstrip("> ").strip()))}</blockquote>')
        elif line.startswith("- "):
            flush_paragraph()
            item = line[2:].strip()
            if not re.match(r"^(证据来源|证据|主要依据来源|相关图片\s*/\s*图纸链接?)[:：]", item):
                list_items.append(display_text(item))
        elif line.startswith("#### "):
            flush_paragraph()
            flush_list()
            html_parts.append(f"<h3>{esc(display_text(line[5:].strip()))}</h3>")
        elif re.match(r"\s*!\[[^\]]*\]\([^)]+\)", line):
            flush_paragraph()
            flush_list()
            continue
        else:
            item = line.strip()
            if not re.match(r"^(证据来源|证据|主要依据来源)[:：]", item):
                paragraph.append(display_text(item))

    flush_paragraph()
    flush_list()
    flush_table()
    return "".join(html_parts), has_table



def render_slide_media(case: dict[str, Any], fallback_index: int, item: dict[str, Any] | None = None, hero: bool = False) -> str:
    # The only automatic placement is the cover image. Chapter imagery must be
    # explicitly embedded in Markdown or matched through related_sections.
    image = case.get("cover") if hero else related_slide_image(case, item)
    if image is None or not image_available(case, image):
        return ""
    register_image_use(case, image)
    classes = "slide-media" + (" hero-media" if hero else "")
    caption = clean(image.get("caption"))
    caption_html = f'<figcaption>{esc(caption)}</figcaption>' if caption else ""
    return f'<figure class="{classes}">{image_tag(image, "")}{caption_html}</figure>'



def related_slide_image(case: dict[str, Any], item: dict[str, Any] | None) -> dict[str, Any] | None:
    if not item:
        return None
    ids = item.get("related_image_ids")
    if not isinstance(ids, list):
        return None
    wanted = {clean(image_id) for image_id in ids if clean(image_id)}
    for image in case["gallery"]:
        if (clean(image.get("id")) in wanted
                and image_available(case, image)
                and image.get("status") == "local" and image.get("src")):
            return image
    return None


def write_index(cases: list[dict[str, Any]]) -> None:
    cases_by_slug = {c["slug"]: c for c in cases}
    featured = [cases_by_slug[slug] for slug in FEATURED_SLUGS if slug in cases_by_slug]
    if not featured:
        featured = [c for c in cases if c["cover"]][:4] or cases[:4]
    hero_case = next((c for c in featured if c.get("cover")), None)
    if hero_case:
        hero_source = hero_case["folder"] / clean(hero_case["cover"].get("src"))
        if hero_source.exists():
            shutil.copy2(hero_source, ASSET_DIR / "hero-case.jpg")
    featured_html = "".join(
        render_case_card(c, "featured", index=index)
        for index, c in enumerate(featured)
    )
    case_cards = "".join(render_case_card(c) for c in cases)
    type_buttons = ["<button class=\"chip is-active\" data-filter=\"type\" data-value=\"all\">全部类型</button>"]
    type_buttons += [
        f"<button class=\"chip\" data-filter=\"type\" data-value=\"{esc(t)}\">{esc(short(t, 18))}</button>"
        for t in sorted({c["type"] for c in cases})
    ]
    region_buttons = ["<button class=\"map-pin is-active\" data-filter=\"region\" data-value=\"all\">全部地区</button>"]
    region_buttons += [
        f"<button class=\"map-pin\" data-filter=\"region\" data-value=\"{esc(r)}\">{esc(r)}</button>"
        for r in sorted({c["region"] for c in cases})
    ]
    status_buttons = ["<button class=\"chip is-active\" data-filter=\"status\" data-value=\"all\">全部状态</button>"]
    status_buttons += [f"<button class=\"chip\" data-filter=\"status\" data-value=\"{esc(s)}\">{esc(short(s, 18))}</button>" for s in sorted({c["status"] for c in cases if c["status"]})]
    year_values = [c["sort_year"] for c in cases if c["sort_year"]]
    year_span = f"{min(year_values)}-{max(year_values)}" if year_values else "Pending"

    body = f"""
    <header class="site-header home-header">
      <a class="brand" href="#"><span>ARCHITECT</span><strong>建筑案例研究库</strong></a>
      <form class="header-search" id="headerSearchForm" role="search">
        <label class="sr-only" for="caseSearch">搜索案例</label>
        <span class="header-search-icon" aria-hidden="true">⌕</span>
        <input id="caseSearch" name="q" type="search" autocomplete="off" placeholder="搜索项目、建筑师、地点或年份" />
        <button type="submit">搜索</button>
      </form>
      <nav class="home-nav" aria-label="首页导航"><a href="#cases">案例库</a><a href="#featured">精选研究</a></nav>
    </header>
    <div id="researchStatus" class="research-status" aria-live="polite" hidden></div>
    <main class="home-main">
      <section class="hero hero--archive" aria-labelledby="home-title">
        <div class="hero-copy">
          <p class="eyebrow">ARCHITECT / CASE STUDY ARCHIVE</p><h1 id="home-title">建筑案例研究库</h1><p class="hero-lead">面向建筑学研究与教学的案例档案。收录可追溯、可验证的建成环境案例，提供图纸、影像、文献与现场记录。</p>
          <a class="primary-action" href="#cases">浏览案例库 <span aria-hidden="true">→</span></a>
        </div>
        <figure class="home-hero-media home-hero-poster" role="img" aria-label="由传统屋顶与当代建筑轮廓组成的建筑研究档案海报">
          <figcaption>ARCHIVE POSTER / 01</figcaption>
        </figure>
      </section>

      <section id="cases" class="section-block case-library">
        <div class="library-head">
          <div><p class="eyebrow">ARCHIVE INDEX</p><h2>案例档案</h2></div>
        </div>
        <div id="caseGrid" class="case-grid">{case_cards}</div>
        <div id="emptyState" class="empty-state" hidden>
          <h3>没有找到匹配案例</h3>
          <p>请调整搜索词或筛选条件，或清除已选条件后重试。</p>
        </div>
      </section>

      <section id="featured" class="section-block">
        <div class="section-heading"><p class="eyebrow">FEATURED RESEARCH</p><h2>精选研究</h2><p>从一项案例进入概念、空间、建造与证据之间的完整阅读。</p></div>
        <div class="featured-grid">{featured_html}</div>
      </section>
    </main>
    """
    (SITE_ROOT / "index.html").write_text(page_shell("建筑案例研究", body, 0), encoding="utf-8")


def write_preview() -> None:
    body = """
    <header class="site-header detail-header preview-header">
      <a class="brand" href="index.html"><span>ARCHITECT</span><strong>建筑案例研究库</strong></a>
      <nav aria-label="预览导航"><a href="index.html">返回案例库</a></nav>
    </header>
    <main id="casePreview" class="preview-main" aria-live="polite">
      <p class="preview-loading">正在读取案例预览。</p>
    </main>
    <script src="./assets/preview.js"></script>
    """
    (SITE_ROOT / "preview.html").write_text(page_shell("案例预览", body, 0), encoding="utf-8")


def render_case_card(case: dict[str, Any], variant: str = "standard", index: int = 0) -> str:
    cover = case["cover"]
    card_title = clean(case["title"]).split(" / ", 1)[0].strip()
    is_standard = variant == "standard"
    classes = "project-card project-card--standard case-card" if is_standard else "project-card project-card--featured featured-card"
    if not is_standard and index % 2 == 1:
        classes += " featured-card--reverse"
    data_attributes = ""
    if is_standard:
        data_attributes = f'''\n      data-type="{esc(case["type"])}"
      data-region="{esc(case["region"])}"
      data-status="{esc(case["status"])}"
      data-year="{case["sort_year"] or 0}"
      data-title="{esc(case["title"].lower())}"
      data-architect="{esc(case["architects_text"].lower())}"
      data-text="{esc(case["search_blob"])}"'''
    return f"""
    <article class="{classes}"{data_attributes}>
      <a href="cases/{esc(case["slug"])}/index.html">
        {render_case_media(case, cover)}
        <div class="project-card-body case-card-body">
          <h3 class="project-card-title">{esc(card_title)}</h3>
          <p class="project-card-summary">{esc(case["summary"])}</p>
          <p class="case-card-meta">
            <span>{esc(card_earliest_year(case))}</span><i class="case-card-meta-separator" aria-hidden="true"></i>
            <span>{esc(card_location(case))}</span><i class="case-card-meta-separator" aria-hidden="true"></i>
            <span>{esc(card_primary_type(case))}</span>
          </p>
        </div>
      </a>
    </article>
    """


def card_earliest_year(case: dict[str, Any]) -> str:
    """Use the earliest documented year for a compact archive-card time marker."""
    years = [int(item) for item in re.findall(r"(?:19|20)\d{2}", clean(case.get("year_text")))]
    return f"{min(years)}年" if years else "年代待定"


def card_primary_type(case: dict[str, Any]) -> str:
    """Show one Chinese-facing program label rather than a long taxonomy string."""
    raw = clean(case.get("program")) or clean(case.get("type")) or "类型待补充"
    primary = re.split(r"\s*(?:/|／|、|，|,|；|;)\s*", raw, maxsplit=1)[0].strip()
    translations = {
        "Cultural": "文化建筑",
        "Conference center": "会议中心",
        "Commercial public complex": "公共建筑",
        "Cultural building": "文化建筑",
        "Cultural experience center": "文化体验中心",
        "Cultural / education / brand experience": "文化体验中心",
        "Commercial complex / community public complex": "社区公共综合体",
        "Renovation / housing / urban renewal": "旧城改造",
        "Cultural / civic conference building": "国际会议中心",
        "Cultural / exposition pavilion / adaptive reuse": "文化展馆",
        "Cultural / urban regeneration": "文化展示建筑",
    }
    if primary and "?" not in primary and re.search(r"[\u4e00-\u9fff]", primary):
        return primary
    return translations.get(clean(case.get("type")), translations.get(primary, "公共建筑"))


def card_location(case: dict[str, Any]) -> str:
    """Condense location to the familiar city-and-country form needed by one-line cards."""
    location = clean(case.get("location"))
    places = ["深圳", "广州", "杭州", "佛山", "苏州", "成都", "合肥", "济宁", "青岛", "台州", "上海", "泰州", "北京", "秦皇岛", "贵阳", "毕节"]
    for city in places:
        if city in location:
            return f"{city}，中国"
    if "Billund" in location or "Denmark" in location:
        return "比隆，丹麦"
    return case.get("region") or location or "地点待补充"


def render_evidence_rail(case: dict[str, Any]) -> str:
    """Shared archive evidence component for index and editorial case entries."""
    status = clean(case.get("status")) or "资料待补充"
    return f"""
          <dl class="evidence-rail" aria-label="案例档案信息">
            <div><dt>年份</dt><dd>{esc(case.get("year_text") or "待定")}</dd></div>
            <div><dt>地点</dt><dd>{esc(case.get("location") or case.get("region") or "待补充")}</dd></div>
            <div><dt>类型</dt><dd>{esc(case.get("type") or "待补充")}</dd></div>
            <div><dt>状态</dt><dd>{esc(status)}</dd></div>
          </dl>
    """


def render_case_media(case: dict[str, Any], cover: dict[str, Any] | None) -> str:
    """Shared thumbnail figure with explicit loading and missing-media states."""
    if not cover:
        return '<figure class="case-card-media is-media-missing" data-media-state aria-label="图片资料待补充"><span class="media-status">图片资料待补充</span></figure>'
    media_text = " ".join(clean(cover.get(key)) for key in ("src", "image_type", "caption")).lower()
    kind = " is-drawing" if re.search(r"plan|section|elevation|drawing|diagram|analysis|site|detail|平面|剖面|总平|分析", media_text) else ""
    return f'''<figure class="case-card-media{kind}" data-media-state>
          {image_tag(cover, f"cases/{case['slug']}/")}
          <span class="media-status" aria-live="polite">图片加载中</span>
        </figure>'''


def render_timeline_card(case: dict[str, Any]) -> str:
    cover = case.get("cover")
    if not cover:
        return ""
    title = clean(case.get("title")).split(" / ", 1)[0].strip()
    year = str(case.get("sort_year")) if case.get("sort_year") else (clean(case.get("year_text")) or "待定")
    media = image_tag(cover, f"cases/{case['slug']}/", loading="eager")
    return f'''
    <article class="timeline-card">
      <a href="cases/{esc(case["slug"])}/index.html" aria-label="查看{esc(title)}案例详情">
        <div class="timeline-card-image">{media}</div>
        <div class="timeline-card-info">
          <span class="timeline-card-year">{esc(year)}</span>
          <h3>{esc(title)}</h3>
        </div>
      </a>
    </article>
    '''


def write_assets() -> None:
    shutil.copy2(SOURCE_DIR / "styles.css", ASSET_DIR / "styles.css")
    shutil.copy2(SOURCE_DIR / "app.js", ASSET_DIR / "app.js")
    shutil.copy2(SOURCE_DIR / "preview.js", ASSET_DIR / "preview.js")
    (SITE_ROOT / "runtime-config.js").write_text(
        f"window.ARCHITECT_API_BASE = {json.dumps(API_BASE)};\n",
        encoding="utf-8",
    )
    source_images = SOURCE_DIR / "assets"
    if source_images.exists():
        shutil.copytree(source_images, ASSET_DIR / "images", dirs_exist_ok=True)


def strip_generated_trailing_whitespace() -> None:
    """Keep checked-in generated HTML clean and reviewable."""
    for path in SITE_ROOT.rglob("*.html"):
        lines = path.read_text(encoding="utf-8").splitlines()
        path.write_text("\n".join(line.rstrip() for line in lines) + "\n", encoding="utf-8")


def page_shell(title: str, body: str, depth: int) -> str:
    prefix = "./" if depth == 0 else "../" * depth
    asset_hash = hashlib.sha256(
        (SOURCE_DIR / "styles.css").read_bytes()
        + (SOURCE_DIR / "app.js").read_bytes()
        + (SOURCE_DIR / "preview.js").read_bytes()
        + API_BASE.encode("utf-8")
    ).hexdigest()[:10]
    template = (TEMPLATE_DIR / "page.html").read_text(encoding="utf-8")
    return (
        template.replace("{{TITLE}}", esc(title))
        .replace("{{ASSET_PREFIX}}", prefix)
        .replace("{{ASSET_VERSION}}", asset_hash)
        .replace("{{BODY}}", body)
    )


def image_items(data: dict[str, Any], folder: Path) -> list[dict[str, Any]]:
    images = []
    for item in list_of_dicts(data.get("image_metadata")):
        file_name = clean(item.get("file_name"))
        local = folder / file_name if file_name else None
        copied = bool(local and local.exists())
        if not copied:
            continue
        images.append(
            {
                "src": file_name if copied else "",
                "id": clean(item.get("id")),
                "asset_id": clean(item.get("asset_id")) or clean(item.get("id")) or file_name,
                "caption": clean(item.get("caption")),
                "image_type": clean(item.get("image_type")),
                "recommended_use": clean(item.get("recommended_use")),
                "related_sections": item.get("related_sections") if isinstance(item.get("related_sections"), list) else [],
                "status": "local" if copied else "reference",
            }
        )
    return images


def pick_cover(gallery: list[dict[str, Any]]) -> dict[str, Any] | None:
    local = [g for g in gallery if g["status"] == "local" and g.get("src")]
    if not local:
        return None
    for item in local:
        if "hero" in item.get("image_type", "") or "01" in item.get("image_type", ""):
            return item
    return local[0]


def image_tag(image: dict[str, Any], prefix: str, loading: str = "lazy") -> str:
    src = prefix + image["src"]
    alt = clean(image.get("caption")) or "architecture case image"
    file_name = Path(clean(image.get("src"))).name
    return (
        f'<img src="{esc(src)}" alt="{esc(alt)}" loading="{esc(loading)}" '
        f'data-image-file="{esc(file_name)}" />'
    )


def tag_html(tags: list[str]) -> str:
    return "".join(f"<span>{esc(tag)}</span>" for tag in tags if tag)


def build_keywords(data: dict[str, Any], case_type: str, strategies: list[dict[str, Any]]) -> list[str]:
    raw = [case_type]
    raw += [clean(s.get("strategy_name")) for s in strategies[:3]]
    lessons = data.get("design_lessons") or {}
    if isinstance(lessons, dict):
        raw += [clean(item) for item in lessons.get("analysis_diagram_potential") or []]
    words: list[str] = []
    for item in raw:
        for chunk in re.split(r"[/,;|]+", item):
            chunk = chunk.strip()
            if 2 <= len(chunk) <= 20 and chunk not in words:
                words.append(chunk)
    return words[:6]


def extract_area(data: dict[str, Any]) -> str:
    metrics = data.get("technical_metrics")
    if isinstance(metrics, dict):
        area = metrics.get("building_area")
        if isinstance(area, dict):
            value = clean(area.get("value"))
            unit = clean(area.get("unit"))
            if value:
                return f"{value} {unit}".strip()
    for fact in list_of_dicts(data.get("key_facts")):
        if "area" in clean(fact.get("label")).lower() or "面积" in clean(fact.get("label")):
            return clean(fact.get("value"))
    return ""


def infer_region(location: str) -> str:
    if "中国" in location or any(name in location for name in ["广东", "江苏", "山东", "上海", "四川", "贵州", "河北", "安徽", "浙江"]):
        return "中国"
    if "Denmark" in location or "Billund" in location:
        return "丹麦"
    return "其他地区"


def extract_sort_year(value: str) -> int | None:
    years = [int(item) for item in re.findall(r"(?:19|20)\d{2}", value)]
    return max(years) if years else None


def normalize_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [clean(item) for item in value if clean(item)]
    if clean(value):
        return [clean(value)]
    return []


def list_of_dicts(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def first_markdown_paragraph(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith(("#", "|", "-", ">", "!")):
            return re.sub(r"[*`]", "", stripped)[:180]
    return ""


def clean(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def short(value: str, length: int) -> str:
    return value if len(value) <= length else value[:length] + "..."


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


if __name__ == "__main__":
    raise SystemExit(main())
