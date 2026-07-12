#!/usr/bin/env python3
"""Build a V0 static architecture case research website."""

from __future__ import annotations

import html
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any


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
    global CASE_ROOT, SITE_ROOT, ASSET_DIR, CASE_SITE_DIR, FEATURED_SLUGS
    config_dir = Path(str(config["_config_path"])).parent
    case_packages_dir = Path(str(config.get("casePackagesDir") or ""))
    output_dir = Path(str(config.get("outputDir") or "public"))
    CASE_ROOT = case_packages_dir if case_packages_dir.is_absolute() else config_dir / case_packages_dir
    SITE_ROOT = output_dir if output_dir.is_absolute() else config_dir / output_dir
    ASSET_DIR = SITE_ROOT / "assets"
    CASE_SITE_DIR = SITE_ROOT / "cases"
    FEATURED_SLUGS = [str(slug) for slug in config.get("featuredSlugs", []) if str(slug).strip()]
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
        year_text = clean(data.get("year")) or "未记录"
        case_type = clean(data.get("case_type") or data.get("program")) or "未分类"
        location = clean(data.get("location")) or "未记录"
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
                "architects_text": " / ".join(architects) if architects else "未记录",
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
    chunks = markdown_deck_chunks(Path(case["md_path"]))
    slides: list[dict[str, str]] = []

    def add(label: str, title: str, body: str, media: str = "", variant: str = "") -> None:
        if not body.strip() and not media.strip():
            return
        number = f"{len(slides) + 1:02d}"
        class_name = "deck-slide" + (f" {variant}" if variant else "")
        slides.append(
            {
                "label": label,
                "html": f"""
                <article class="{class_name}" data-slide data-slide-label="{esc(label)}" data-screen-label="{number} {esc(label)}">
                  <div class="slide-grid">
                    <div class="slide-copy">
                      <p class="section-number">{number}</p>
                      <h1>{esc(title)}</h1>
                      {body}
                    </div>
                    {media}
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
        body, media, has_table = render_markdown_slide_content(case, chunk["lines"], index, text_only)
        variants = []
        content_length = len("".join(chunk["lines"]))
        if has_table or content_length > 420:
            variants.append("is-dense")
        if content_length > 750:
            variants.append("is-compact")
        if text_only:
            variants.append("is-text-only")
        if is_basic_info_slide(chunk["title"]):
            variants.append("is-basic-info")
        if "is-transposed" in body:
            variants.append("has-wide-table")
        add(
            chunk["label"],
            display_slide_title(chunk["title"]),
            body,
            "" if text_only else media or render_slide_media(case, index),
            " ".join(variants),
        )

    compact_sources = render_compact_sources(case["sources"])
    if compact_sources:
        add("资料", "参考资料", compact_sources, "", "is-appendix is-text-only")

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


def is_basic_info_slide(title: str) -> bool:
    normalized = re.sub(r"\s+", "", title)
    return "基本信息" in normalized and ("技术指标" in normalized or "经济技术指标" in normalized or normalized.endswith("基本信息"))


def should_skip_markdown_chunk(title: str) -> bool:
    normalized = re.sub(r"\s+", "", title).lower()
    skip_keywords = [
        "资料质量",
        "证据密度",
        "证据",
        "图纸与图片索引",
        "图片索引",
        "信息缺口",
        "冲突",
        "来源列表",
        "levela",
        "levelb",
        "levelc",
        "leveld",
    ]
    return any(keyword.lower() in normalized for keyword in skip_keywords)


def is_text_only_slide(title: str) -> bool:
    normalized = re.sub(r"\s+", "", title).lower()
    text_only_keywords = [
        "基本信息",
        "经济技术指标",
        "场地信息表",
        "对我的设计启发",
        "设计启发",
        "参考资料",
        "来源",
    ]
    return any(keyword.lower() in normalized for keyword in text_only_keywords)


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


def render_markdown_slide_content(case: dict[str, Any], lines: list[str], fallback_index: int, text_only: bool = False) -> tuple[str, str, bool]:
    image_line, remaining = extract_first_markdown_image(lines)
    media = "" if text_only else render_markdown_image_media(case, image_line) if image_line else ""
    body, has_table = render_markdown_fragment(remaining)
    return body, media, has_table


def extract_first_markdown_image(lines: list[str]) -> tuple[str, list[str]]:
    for index, line in enumerate(lines):
        if re.match(r"\s*!\[[^\]]*\]\([^)]+\)", line):
            return line, lines[:index] + lines[index + 1 :]
    return "", lines


def render_markdown_image_media(case: dict[str, Any], line: str) -> str:
    match = re.match(r"\s*!\[([^\]]*)\]\(([^)]+)\)", line)
    if not match:
        return ""
    alt = clean(match.group(1)) or "case image"
    src = clean(match.group(2))
    file_name = Path(src).name
    for image in case["gallery"]:
        if Path(clean(image.get("src"))).name == file_name:
            return f'<figure class="slide-media">{image_tag(image, "")}<figcaption>{esc(alt)}</figcaption></figure>'
    return f'<figure class="slide-media"><img src="{esc(src)}" alt="{esc(alt)}" loading="lazy" /><figcaption>{esc(alt)}</figcaption></figure>'


def render_markdown_fragment(lines: list[str]) -> tuple[str, bool]:
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
        nonlocal list_items
        if list_items:
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
            if not row or not re.search(r"^(证据|证据来源|主要依据来源)[:：]?$", row[0])
        ]
        if head:
            evidence_indexes = {index for index, cell in enumerate(head) if "证据" in cell}
            if evidence_indexes:
                head = [cell for index, cell in enumerate(head) if index not in evidence_indexes]
                body_rows = [
                    [cell for index, cell in enumerate(row) if index not in evidence_indexes]
                    for row in body_rows
                ]
        should_transpose_site_table = (
            len(head) == 2
            and len(body_rows) <= 8
            and any("场地" in cell for cell in head)
            and all(len(row) >= 2 for row in body_rows)
        )
        should_transpose_basic_table = (
            len(head) == 2
            and [clean(cell) for cell in head] == ["项目", "内容"]
            and all(len(row) >= 2 for row in body_rows)
        )
        if should_transpose_basic_table:
            items = normalize_basic_info_rows(body_rows)
            html_parts.append(render_fact_list(items))
        elif should_transpose_site_table:
            labels = [row[0] for row in body_rows if clean(row[0]) or clean(row[1])]
            values = [row[1] for row in body_rows if clean(row[0]) or clean(row[1])]
            html_parts.append(render_transposed_table(labels, values))
        else:
            thead = "<thead><tr>" + "".join(f"<th>{esc(display_text(cell))}</th>" for cell in head) + "</tr></thead>" if head else ""
            tbody = "<tbody>" + "".join("<tr>" + "".join(f"<td>{esc(display_text(cell))}</td>" for cell in row) + "</tr>" for row in body_rows) + "</tbody>"
            html_parts.append(f'<div class="table-wrap markdown-table"><table class="data-table">{thead}{tbody}</table></div>')
        has_table = True
        table_rows = []

    for raw in lines:
        line = raw.rstrip()
        presentation_note = line.strip().strip("*_ ")
        if re.match(r"^(图像用途|图文相关性|图片说明|配图说明)[:：]", presentation_note):
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
            if not re.match(r"^(证据来源|证据|主要依据来源|相关图片\s*/\s*图纸)[:：]", item):
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
    image = related_slide_image(case, item) if item else None
    local_gallery = [img for img in case["gallery"] if img.get("status") == "local" and img.get("src")]
    if image is None and local_gallery:
        image = local_gallery[min(fallback_index, len(local_gallery) - 1)]
    if image is None:
        return '<figure class="slide-media text-media"><span>图片资料待补充</span></figure>'
    caption = clean(image.get("caption")) or clean(image.get("image_type")) or "案例图片"
    classes = "slide-media" + (" hero-media" if hero else "")
    return f'<figure class="{classes}">{image_tag(image, "")}<figcaption>{esc(caption)}</figcaption></figure>'



def related_slide_image(case: dict[str, Any], item: dict[str, Any] | None) -> dict[str, Any] | None:
    if not item:
        return None
    ids = item.get("related_image_ids")
    if not isinstance(ids, list):
        return None
    wanted = {clean(image_id) for image_id in ids if clean(image_id)}
    for image in case["gallery"]:
        if clean(image.get("id")) in wanted and image.get("status") == "local" and image.get("src"):
            return image
    return None


def write_index(cases: list[dict[str, Any]]) -> None:
    cases_by_slug = {c["slug"]: c for c in cases}
    featured = [cases_by_slug[slug] for slug in FEATURED_SLUGS if slug in cases_by_slug]
    if not featured:
        featured = [c for c in cases if c["cover"]][:4] or cases[:4]
    featured_html = "".join(render_case_card(c, "featured") for c in featured)
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
    year_values = [c["sort_year"] for c in cases if c["sort_year"]]
    year_span = f"{min(year_values)}-{max(year_values)}" if year_values else "待整理"

    body = f"""
    <header class="site-header">
      <a class="brand" href="#"><span>ARCHIVE</span><strong>建筑案例研究</strong></a>
      <nav><a href="#featured">精选</a><a href="#cases">案例库</a></nav>
    </header>
    <main>
      <section class="hero">
        <div class="hero-copy">
          <p class="eyebrow">ARCHITECTURE CASE RESEARCH</p>
          <h1>建筑案例研究库</h1>
        </div>
        <div class="hero-panel" aria-label="资料概览">
          <div><strong>{len(cases)}</strong><span>案例包</span></div>
          <div><strong>{sum(c["image_count"] for c in cases)}</strong><span>图片 / 图纸记录</span></div>
          <div><strong>{sum(c["source_count"] for c in cases)}</strong><span>参考来源</span></div>
          <div><strong>{year_span}</strong><span>年份跨度</span></div>
        </div>
      </section>

      <section id="featured" class="section-block">
        <div class="section-heading">
          <p class="eyebrow">SELECTED CASES</p>
          <h2>精选案例</h2>
        </div>
        <div class="featured-grid">{featured_html}</div>
      </section>

      <section id="cases" class="section-block case-library">
        <div class="library-head">
          <div>
            <p class="eyebrow">CASE LIBRARY</p>
            <h2>案例列表</h2>
          </div>
        </div>
        <div class="library-toolbar">
          <input id="caseSearch" type="search" aria-label="搜索案例" placeholder="搜索项目、建筑师、地点、年份、类型或设计策略" />
          <label class="sort-control">排序
            <select id="sortSelect">
              <option value="year-desc">年份从新到旧</option>
              <option value="year-asc">年份从旧到新</option>
              <option value="title-asc">项目名称 A-Z</option>
              <option value="architect-asc">建筑师 A-Z</option>
            </select>
          </label>
        </div>
        <div class="filter-panel">
          <div class="filter-group"><h3>建筑类型</h3><div class="chip-row">{"".join(type_buttons)}</div></div>
          <div class="filter-group"><h3>国家 / 地区</h3><div class="chip-row">{"".join(region_buttons)}</div></div>
        </div>
        <div id="activeFilters" class="active-filters"></div>
        <div id="caseGrid" class="case-grid">{case_cards}</div>
        <div id="emptyState" class="empty-state" hidden>
          <h3>没有找到匹配案例</h3>
          <p>请调整搜索词或筛选条件。</p>
        </div>
      </section>
    </main>
    """
    (SITE_ROOT / "index.html").write_text(page_shell("建筑案例研究", body, 0), encoding="utf-8")


def render_case_card(case: dict[str, Any], variant: str = "standard") -> str:
    cover = case["cover"]
    media = image_tag(cover, f"cases/{case['slug']}/") if cover else ""
    is_standard = variant == "standard"
    classes = "project-card project-card--standard case-card" if is_standard else "project-card project-card--featured featured-card"
    data_attributes = ""
    if is_standard:
        data_attributes = f'''\n      data-type="{esc(case["type"])}"
      data-region="{esc(case["region"])}"
      data-year="{case["sort_year"] or 0}"
      data-title="{esc(case["title"].lower())}"
      data-architect="{esc(case["architects_text"].lower())}"
      data-text="{esc(case["search_blob"])}"'''
    return f"""
    <article class="{classes}"{data_attributes}>
      <a href="cases/{esc(case["slug"])}/index.html">
        {media}
        <div class="project-card-body case-card-body">
          <div class="card-meta"><span>{esc(case["year_text"])}</span><span>{esc(case["region"])}</span></div>
          <h3 class="project-card-title">{esc(case["title"])}</h3>
          <p class="project-card-summary">{esc(case["summary"])}</p>
          <dl class="project-card-facts">
            <div class="project-card-fact"><dt>建筑师</dt><dd>{esc(case["architects_text"])}</dd></div>
            <div class="project-card-fact"><dt>类型</dt><dd>{esc(case["type"])}</dd></div>
          </dl>
          <div class="project-card-tags tag-row">{tag_html(case["keywords"][:3])}</div>
        </div>
      </a>
    </article>
    """


def write_assets() -> None:
    shutil.copy2(SOURCE_DIR / "styles.css", ASSET_DIR / "styles.css")
    shutil.copy2(SOURCE_DIR / "app.js", ASSET_DIR / "app.js")


def page_shell(title: str, body: str, depth: int) -> str:
    prefix = "./" if depth == 0 else "../" * depth
    asset_hash = hashlib.sha256(
        (SOURCE_DIR / "styles.css").read_bytes() + (SOURCE_DIR / "app.js").read_bytes()
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
                "caption": clean(item.get("caption")),
                "image_type": clean(item.get("image_type")),
                "recommended_use": clean(item.get("recommended_use")),
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


def image_tag(image: dict[str, Any], prefix: str) -> str:
    src = prefix + image["src"]
    return f'<img src="{esc(src)}" alt="{esc(image.get("caption") or "建筑案例图片")}" loading="lazy" />'


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
        for chunk in re.split(r"[/,，;；、]", item):
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
