#!/usr/bin/env python3
"""Build a V0 static architecture case research website."""

from __future__ import annotations

import html
import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config.example.json"
LOCAL_CONFIG = ROOT / "config.local.json"
CASE_ROOT = Path()
SITE_ROOT = Path()
ASSET_DIR = Path()
CASE_SITE_DIR = Path()


def main() -> int:
    configure_paths(load_config())
    cases = load_cases()
    if not cases:
        raise SystemExit("No cases found.")

    if SITE_ROOT.exists():
        shutil.rmtree(SITE_ROOT)
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
    global CASE_ROOT, SITE_ROOT, ASSET_DIR, CASE_SITE_DIR
    config_dir = Path(str(config["_config_path"])).parent
    case_packages_dir = Path(str(config.get("casePackagesDir") or ""))
    output_dir = Path(str(config.get("outputDir") or "public"))
    CASE_ROOT = case_packages_dir if case_packages_dir.is_absolute() else config_dir / case_packages_dir
    SITE_ROOT = output_dir if output_dir.is_absolute() else config_dir / output_dir
    ASSET_DIR = SITE_ROOT / "assets"
    CASE_SITE_DIR = SITE_ROOT / "cases"
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
    progress_html = "".join(
        f'<button type="button" data-slide-target="{index}" aria-label="Slide {index + 1}" title="{esc(slide["label"])}"><span>{index + 1:02d}</span></button>'
        for index, slide in enumerate(slides)
    )

    body = f"""
    <header class="site-header detail-header">
      <a class="brand" href="../../index.html"><span>ARCHIVE</span><strong>建筑案例研究</strong></a>
      <nav><a href="../../index.html#cases">案例库</a><a href="../../index.html#about">关于</a></nav>
    </header>
    <main class="detail case-deck" data-case-deck>
      <section class="deck-stage" aria-live="polite">
        {slides_html}
      </section>
      <footer class="deck-controls">
        <button class="deck-arrow" type="button" data-slide-prev aria-label="上一页">&lsaquo;</button>
        <div class="deck-progress" role="tablist">{progress_html}</div>
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
                <article class="{class_name}" data-slide data-screen-label="{number} {esc(label)}">
                  <div class="slide-grid">
                    <div class="slide-copy">
                      <a class="back-link" href="../../index.html#cases">返回案例库</a>
                      <p class="section-number">{number}</p>
                      <p class="eyebrow">CASE.MD DECK</p>
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
        f'<p class="slide-lead">{esc(case["summary"])}</p><div class="detail-tags">{tag_html(case["keywords"][:5])}</div>',
        render_slide_media(case, 0, hero=True),
        "is-cover",
    )

    for index, chunk in enumerate(chunks, 1):
        if should_skip_markdown_chunk(chunk["title"]):
            continue
        text_only = is_text_only_slide(chunk["title"])
        body, media, has_table = render_markdown_slide_content(case, chunk["lines"], index, text_only)
        variants = []
        if has_table or len("".join(chunk["lines"])) > 1100:
            variants.append("is-scrollable")
        if text_only:
            variants.append("is-text-only")
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
    return title


def should_skip_markdown_chunk(title: str) -> bool:
    normalized = re.sub(r"\s+", "", title).lower()
    skip_keywords = [
        "资料质量",
        "证据密度",
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
    return '<p class="slide-lead source-lead">资料来源仅作为附录保留，主线以案例分析内容为准。</p><ul class="compact-source-list">' + "".join(items) + "</ul>"


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
        thead = "<thead><tr>" + "".join(f"<th>{esc(cell)}</th>" for cell in head) + "</tr></thead>" if head else ""
        tbody = "<tbody>" + "".join("<tr>" + "".join(f"<td>{esc(cell)}</td>" for cell in row) + "</tr>" for row in body_rows) + "</tbody>"
        html_parts.append(f'<div class="table-wrap markdown-table"><table class="data-table">{thead}{tbody}</table></div>')
        has_table = True
        table_rows = []

    for raw in lines:
        line = raw.rstrip()
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
            html_parts.append(f'<blockquote>{esc(line.lstrip("> ").strip())}</blockquote>')
        elif line.startswith("- "):
            flush_paragraph()
            list_items.append(line[2:].strip())
        elif line.startswith("#### "):
            flush_paragraph()
            flush_list()
            html_parts.append(f"<h3>{esc(line[5:].strip())}</h3>")
        elif re.match(r"\s*!\[[^\]]*\]\([^)]+\)", line):
            flush_paragraph()
            flush_list()
            match = re.match(r"\s*!\[([^\]]*)\]\(([^)]+)\)", line)
            if match:
                html_parts.append(f'<figure class="inline-md-image"><img src="{esc(match.group(2))}" alt="{esc(match.group(1))}" loading="lazy" /></figure>')
        else:
            paragraph.append(line.strip())

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


def build_structured_case_sections(case: dict[str, Any]) -> list[dict[str, str]]:
    data = case["data"]
    sections: list[dict[str, str]] = []

    def add(section_id: str, label: str, title: str, body: str) -> None:
        if not body.strip():
            return
        number = f"{len(sections) + 1:02d}"
        sections.append(
            {
                "id": section_id,
                "label": label,
                "html": f"""
                <section id="{section_id}" class="note-section">
                  <p class="section-number">{number}</p>
                  <h2>{esc(title)}</h2>
                  {body}
                </section>
                """,
            }
        )

    add(
        "basic",
        "基本信息",
        "基本信息",
        render_key_value_table(
            [
                ("项目名称", case["title"]),
                ("建筑师", case["architects_text"]),
                ("地点", case["location"]),
                ("年份", case["year_text"]),
                ("类型", case["type"]),
                ("功能", case["program"]),
                ("状态", case["status"]),
                ("面积", case["area"] or "未确认"),
                ("资料可信度", case["confidence"]),
            ]
        )
        + render_key_facts(data.get("key_facts")),
    )

    concept = data.get("design_concept")
    add(
        "overview",
        "概述与概念",
        "项目概述与设计概念",
        f'<p class="lead-copy">{esc(case["summary"])}</p>'
        + render_named_text_block("资料中的概念", clean(concept.get("sourced_concept")) if isinstance(concept, dict) else "")
        + render_named_text_block("综合判断", clean(concept.get("ai_synthesis")) if isinstance(concept, dict) else ""),
    )

    add("strategies", "设计策略", "核心设计策略", render_strategies_full(case["strategies"]))
    add("site-context", "场地关系", "场地关系", render_text_evidence(case["site"]))
    add("spatial", "空间组织", "空间与流线", render_text_evidence(case["spatial"]))
    add("materials", "结构材料", "结构、材料与建造", render_text_evidence(case["materials"]))
    add("technical", "技术指标", "技术指标", render_technical_metrics(data.get("technical_metrics")))
    add("site-info", "场地信息", "场地信息表", render_nested_text_dict(data.get("site_information")))
    add("conceptual", "概念探索", "概念创意探索", render_nested_text_dict(data.get("conceptual_exploration")))
    add("language", "建筑语言", "建筑语言生成", render_nested_text_dict(data.get("architectural_language_generation")))
    add("construction", "建造控制", "建造品质控制", render_nested_text_dict(data.get("construction_quality_control")))
    add("lessons", "方法提炼", "核心方法提炼", render_design_lessons(data.get("design_lessons")))
    add("gallery", "图片资料", "图片资料", render_gallery(case))
    add("sources", "参考来源", "参考来源与信息缺口", render_sources(case["sources"]) + render_warnings(case["warnings"]))
    return sections


def render_key_value_table(rows: list[tuple[str, str]]) -> str:
    valid = [(label, value) for label, value in rows if clean(value)]
    if not valid:
        return ""
    body = "".join(f"<tr><th>{esc(label)}</th><td>{esc(value)}</td></tr>" for label, value in valid)
    return f'<div class="table-wrap"><table class="data-table"><tbody>{body}</tbody></table></div>'


def render_key_facts(value: Any) -> str:
    facts = list_of_dicts(value)
    if not facts:
        return ""
    rows = []
    for fact in facts:
        label = clean(fact.get("label"))
        text = clean(fact.get("value"))
        if label or text:
            rows.append(f"<tr><th>{esc(label)}</th><td>{esc(text)}{render_source_ids(fact)}</td></tr>")
    if not rows:
        return ""
    return '<h3>关键事实</h3><div class="table-wrap"><table class="data-table"><tbody>' + "".join(rows) + "</tbody></table></div>"


def render_quality_panel(value: Any, incomplete_reason: Any) -> str:
    if not isinstance(value, dict):
        reason = clean(incomplete_reason)
        return f'<div class="quality-panel"><strong>资料状态</strong><p>{esc(reason)}</p></div>' if reason else ""
    items = []
    status = clean(value.get("source_sufficiency_status"))
    media_count = clean(value.get("architecture_media_count"))
    primary = value.get("has_primary_sources")
    coverage = value.get("analysis_coverage")
    if status:
        items.append(("资料充分度", status))
    if primary is not None:
        items.append(("一级资料", "有" if primary else "无"))
    if media_count:
        items.append(("建筑媒体", f"{media_count} 个"))
    if isinstance(coverage, list) and coverage:
        items.append(("覆盖方向", " / ".join(clean(item) for item in coverage[:6] if clean(item))))
    reason = clean(incomplete_reason)
    rows = "".join(f"<div><dt>{esc(label)}</dt><dd>{esc(text)}</dd></div>" for label, text in items if text)
    note = f"<p>{esc(reason)}</p>" if reason else ""
    return f'<div class="quality-panel"><strong>资料质量</strong><dl>{rows}</dl>{note}</div>' if rows or note else ""


def render_named_text_block(title: str, text: str) -> str:
    if not clean(text):
        return ""
    return f'<div class="structured-card"><h3>{esc(title)}</h3><p>{esc(text)}</p></div>'


def render_strategies_full(strategies: list[dict[str, Any]]) -> str:
    if not strategies:
        return '<p class="muted">当前案例包暂未提供核心策略字段。</p>'
    cards = []
    fields = [
        ("design_problem", "面对的问题"),
        ("specific_approach", "具体做法"),
        ("architectural_effect", "建筑效果"),
        ("evidence", "证据"),
        ("transferable_lesson", "可迁移方法"),
    ]
    for index, item in enumerate(strategies, 1):
        rows = []
        for key, label in fields:
            text = clean(item.get(key))
            if text:
                rows.append(f"<div><dt>{esc(label)}</dt><dd>{esc(text)}</dd></div>")
        related = render_related_images(item)
        source_ids = render_source_ids(item)
        cards.append(
            f"""
            <article class="full-strategy">
              <span>{index:02d}</span>
              <h3>{esc(clean(item.get("strategy_name")) or "设计策略")}</h3>
              <dl>{''.join(rows)}</dl>
              {related}
              {source_ids}
            </article>
            """
        )
    return '<div class="full-strategy-list">' + "".join(cards) + "</div>"


def render_text_evidence(items: list[dict[str, Any]]) -> str:
    if not items:
        return '<p class="muted">当前案例包暂未提供这一组结构化资料。</p>'
    cards = []
    for item in items:
        text = clean(item.get("text"))
        if not text:
            continue
        evidence = clean(item.get("evidence_type"))
        cards.append(
            f"""
            <article class="evidence-card">
              <p>{esc(text)}</p>
              <div class="evidence-meta">
                {f'<span>{esc(evidence)}</span>' if evidence else ''}
                {render_related_images(item)}
                {render_source_ids(item)}
              </div>
            </article>
            """
        )
    return '<div class="evidence-grid">' + "".join(cards) + "</div>" if cards else '<p class="muted">当前案例包暂未提供这一组结构化资料。</p>'


def render_technical_metrics(value: Any) -> str:
    if not isinstance(value, dict) or not value:
        return ""
    rows = []
    label_map = {
        "site_area": "场地面积",
        "building_area": "建筑面积",
        "height": "高度",
        "floors": "层数",
        "far": "容积率",
        "building_density": "建筑密度",
        "structure_system": "结构体系",
        "client": "业主 / 委托方",
        "notes": "备注",
    }
    for key, raw in value.items():
        if key in {"main_materials", "photography_drawing_credits"}:
            continue
        label = label_map.get(key, key)
        if isinstance(raw, dict):
            text = clean(raw.get("value"))
            unit = clean(raw.get("unit"))
            confidence = clean(raw.get("confidence"))
            notes = clean(raw.get("notes"))
            detail = " ".join(part for part in [text, unit] if part).strip()
            if notes:
                detail += f"；{notes}"
            if confidence:
                detail += f"（{confidence}）"
        else:
            detail = clean(raw)
        if detail:
            rows.append(f"<tr><th>{esc(label)}</th><td>{esc(detail)}</td></tr>")
    extra = ""
    if isinstance(value.get("main_materials"), list):
        extra += '<h3>主要材料</h3>' + render_text_evidence(list_of_dicts(value.get("main_materials")))
    if isinstance(value.get("photography_drawing_credits"), list):
        extra += '<h3>图纸与摄影信息</h3>' + render_text_evidence(list_of_dicts(value.get("photography_drawing_credits")))
    table = '<div class="table-wrap"><table class="data-table"><tbody>' + "".join(rows) + "</tbody></table></div>" if rows else ""
    return table + extra


def render_nested_text_dict(value: Any) -> str:
    if not isinstance(value, dict) or not value:
        return ""
    blocks = []
    for key, raw in value.items():
        title = humanize_key(key)
        if isinstance(raw, list):
            rendered = render_text_evidence(list_of_dicts(raw))
            if rendered:
                blocks.append(f'<div class="subsection-block"><h3>{esc(title)}</h3>{rendered}</div>')
        elif isinstance(raw, dict):
            rendered = render_nested_text_dict(raw)
            if rendered:
                blocks.append(f'<div class="subsection-block"><h3>{esc(title)}</h3>{rendered}</div>')
        else:
            text = clean(raw)
            if text:
                blocks.append(f'<div class="structured-card"><h3>{esc(title)}</h3><p>{esc(text)}</p></div>')
    return "".join(blocks)


def render_design_lessons(value: Any) -> str:
    if not isinstance(value, dict) or not value:
        return ""
    parts = []
    if isinstance(value.get("transferable_methods"), list):
        parts.append('<h3>可迁移方法</h3>' + render_text_evidence(list_of_dicts(value.get("transferable_methods"))))
    if isinstance(value.get("avoid_copying"), list):
        parts.append('<h3>不宜直接照抄</h3>' + render_text_evidence(list_of_dicts(value.get("avoid_copying"))))
    diagrams = value.get("analysis_diagram_potential")
    if isinstance(diagrams, list) and diagrams:
        items = "".join(f"<li>{esc(clean(item))}</li>" for item in diagrams if clean(item))
        parts.append(f'<h3>可转化的分析图</h3><ul class="compact-list">{items}</ul>')
    return "".join(parts)


def render_related_images(item: dict[str, Any]) -> str:
    ids = item.get("related_image_ids")
    if not isinstance(ids, list) or not ids:
        return ""
    links = []
    for image_id in ids:
        clean_id = clean(image_id)
        if clean_id:
            links.append(f'<a class="source-chip" href="#image-{esc(clean_id)}">图像 {esc(clean_id)}</a>')
    return "".join(links)


def render_source_ids(item: dict[str, Any]) -> str:
    ids = item.get("source_ids")
    if not isinstance(ids, list) or not ids:
        return ""
    links = []
    for source_id in ids:
        clean_id = clean(source_id)
        if clean_id:
            links.append(f'<a class="source-chip" href="#source-{esc(clean_id)}">来源 {esc(clean_id)}</a>')
    return "".join(links)


def humanize_key(key: str) -> str:
    labels = {
        "location_role": "区位角色",
        "natural_environment": "自然环境",
        "cultural_environment": "文化环境",
        "terrain_conditions": "地形条件",
        "roads_and_access": "道路与进入",
        "surrounding_buildings": "周边建筑",
        "served_users": "服务人群",
        "core_site_tension": "场地核心矛盾",
        "diagnosis": "诊断",
        "positioning": "定位",
        "strategy": "策略",
        "imagery_and_expression": "意象与表达",
        "function": "功能梳理",
        "layout": "布局逻辑",
        "composition": "形体构成",
        "place_atmosphere": "场所与氛围",
        "construction_language": "建造语言",
        "materials_and_craft": "材料与工艺",
        "tectonic_logic": "构造逻辑",
        "performance_and_construction_control": "物理性能与施工控制",
    }
    return labels.get(key, key.replace("_", " ").title())


def write_index(cases: list[dict[str, Any]]) -> None:
    featured = [c for c in cases if c["cover"]][:4] or cases[:4]
    featured_html = "".join(render_featured_card(c, i) for i, c in enumerate(featured))
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
      <nav><a href="#featured">精选</a><a href="#cases">案例库</a><a href="#about">关于</a></nav>
    </header>
    <main>
      <section class="hero">
        <div class="hero-copy">
          <p class="eyebrow">ARCHITECTURE CASE RESEARCH</p>
          <h1>建筑案例研究库</h1>
          <p>从本地 <code>case-packages</code> 汇总真实案例资料，按项目事实、设计策略、场地关系、空间组织、结构材料与来源证据重新组织。</p>
          <form class="hero-search" action="#cases">
            <input id="caseSearch" type="search" placeholder="搜索项目、建筑师、地点、年份、类型或设计策略" />
            <button type="submit">搜索</button>
          </form>
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
          <p>优先展示已有本地图像的案例，让首页先有作品集式的视觉入口。</p>
        </div>
        <div class="featured-grid">{featured_html}</div>
      </section>

      <section class="section-block taxonomy">
        <div class="section-heading">
          <p class="eyebrow">ENTRY POINTS</p>
          <h2>分类入口</h2>
          <p>类型、地区和研究主题都来自现有静态数据，v0 不编造额外案例。</p>
        </div>
        <div class="taxonomy-grid">
          <div class="taxonomy-card">
            <h3>建筑类型</h3>
            <div class="chip-row">{"".join(type_buttons)}</div>
          </div>
          <div class="taxonomy-card map-card">
            <h3>国家 / 地区</h3>
            <div class="map-surface">{"".join(region_buttons)}</div>
          </div>
          <div class="taxonomy-card coming-soon">
            <h3>AI 补充案例</h3>
            <p>未来可接入建筑案例研究 Skill 自动补充新案例。当前为静态原型入口，暂不执行生成。</p>
            <button disabled>Coming Soon</button>
          </div>
        </div>
      </section>

      <section id="cases" class="section-block case-library">
        <div class="library-head">
          <div>
            <p class="eyebrow">CASE LIBRARY</p>
            <h2>案例列表</h2>
          </div>
          <label class="sort-control">排序
            <select id="sortSelect">
              <option value="year-desc">年份从新到旧</option>
              <option value="year-asc">年份从旧到新</option>
              <option value="title-asc">项目名称 A-Z</option>
              <option value="architect-asc">建筑师 A-Z</option>
            </select>
          </label>
        </div>
        <div id="activeFilters" class="active-filters"></div>
        <div id="caseGrid" class="case-grid">{case_cards}</div>
        <div id="emptyState" class="empty-state" hidden>
          <h3>没有找到匹配案例</h3>
          <p>可以调整搜索词或清空筛选。AI 自动补充案例入口将在后续版本接入。</p>
        </div>
      </section>

      <section id="about" class="section-block about">
        <div>
          <p class="eyebrow">ABOUT</p>
          <h2>一个面向建筑学习和研究的案例工具。</h2>
        </div>
        <p>v0 只读取本地静态案例包，不接后端、不接数据库、不做真实登录。后续可以在这个基础上加入案例库管理、AI 生成、资料质量检查和研究工作流。</p>
      </section>
    </main>
    """
    (SITE_ROOT / "index.html").write_text(page_shell("建筑案例研究", body, 0), encoding="utf-8")


def render_featured_card(case: dict[str, Any], index: int) -> str:
    cover = case["cover"]
    image = image_tag(cover, f"cases/{case['slug']}/") if cover else ""
    return f"""
    <article class="featured-card">
      <a href="cases/{esc(case['slug'])}/index.html">
        {image}
        <div>
          <span>{esc(case["year_text"])}</span>
          <h3>{esc(case["title"])}</h3>
          <p>{esc(case["summary"])}</p>
        </div>
      </a>
    </article>
    """


def render_case_card(case: dict[str, Any]) -> str:
    cover = case["cover"]
    media = image_tag(cover, f"cases/{case['slug']}/") if cover else ""
    return f"""
    <article class="case-card"
      data-type="{esc(case["type"])}"
      data-region="{esc(case["region"])}"
      data-year="{case["sort_year"] or 0}"
      data-title="{esc(case["title"].lower())}"
      data-architect="{esc(case["architects_text"].lower())}"
      data-text="{esc(case["search_blob"])}">
      <a href="cases/{esc(case["slug"])}/index.html">
        {media}
        <div class="case-card-body">
          <div class="card-meta"><span>{esc(case["year_text"])}</span><span>{esc(case["region"])}</span></div>
          <h3>{esc(case["title"])}</h3>
          <p>{esc(case["summary"])}</p>
          <dl>
            <div><dt>建筑师</dt><dd>{esc(case["architects_text"])}</dd></div>
            <div><dt>类型</dt><dd>{esc(case["type"])}</dd></div>
          </dl>
          <div class="tag-row">{tag_html(case["keywords"][:3])}</div>
        </div>
      </a>
    </article>
    """


def render_detail_hero_media(case: dict[str, Any]) -> str:
    if case["cover"]:
        return f'<figure class="detail-media">{image_tag(case["cover"], "")}<figcaption>{esc(case["cover"].get("caption"))}</figcaption></figure>'
    return '<div class="detail-media text-media"><span>图像资料待补充</span></div>'


def render_strategy(item: dict[str, Any], number: int) -> str:
    return f"""
    <div class="strategy-card">
      <span>{number:02d}</span>
      <h3>{esc(clean(item.get("strategy_name")) or "策略")}</h3>
      <p>{esc(clean(item.get("specific_approach")) or clean(item.get("architectural_effect")) or clean(item.get("design_problem")))}</p>
    </div>
    """


def render_note_list(items: list[dict[str, Any]], title: str) -> str:
    number = {"场地关系": "03", "空间组织": "04", "结构材料": "05"}.get(title, "")
    if not items:
        body = "<p>当前案例包暂未提供这一组结构化资料。</p>"
    else:
        body = "<div class=\"note-list\">" + "".join(f"<p>{esc(clean(item.get('text')))}</p>" for item in items if clean(item.get("text"))) + "</div>"
    return f'<p class="section-number">{number}</p><h2>{esc(title)}</h2>{body}'


def render_gallery(case: dict[str, Any]) -> str:
    local_gallery = [img for img in case["gallery"] if img.get("status") == "local" and img.get("src")]
    if not local_gallery:
        return '<p class="muted">当前案例包没有可用于本地展示的图片记录。</p>'
    items = []
    for img in local_gallery[:8]:
        media = image_tag(img, "")
        image_id = clean(img.get("id")) or clean(img.get("image_type"))
        figure_id = f' id="image-{esc(image_id)}"' if image_id else ""
        meta = " / ".join(part for part in [clean(img.get("image_type")), clean(img.get("recommended_use"))] if part)
        caption = esc(img.get("caption") or img.get("image_type") or "图片资料")
        items.append(f'<figure{figure_id}>{media}<figcaption><strong>{caption}</strong>{f"<span>{esc(meta)}</span>" if meta else ""}</figcaption></figure>')
    return '<div class="gallery-grid">' + "".join(items) + "</div>"


def render_sources(sources: list[dict[str, Any]]) -> str:
    if not sources:
        return '<p class="muted">暂无来源记录。</p>'
    rows = []
    for source in sources:
        source_id = clean(source.get("id"))
        title = clean(source.get("title")) or clean(source.get("url")) or "来源"
        url = clean(source.get("url")) or "#"
        publisher = clean(source.get("publisher"))
        level = clean(source.get("source_level"))
        item_id = f' id="source-{esc(source_id)}"' if source_id else ""
        notes = clean(source.get("notes"))
        rows.append(
            f'<li{item_id}><a href="{esc(url)}">{esc(title)}</a><span>{esc(level)}</span><em>{esc(publisher)}</em>'
            f'{f"<p>{esc(notes)}</p>" if notes else ""}</li>'
        )
    return '<ul class="source-list">' + "".join(rows) + "</ul>"


def render_warnings(warnings: list[dict[str, Any]]) -> str:
    if not warnings:
        return ""
    items = "".join(f"<li>{esc(clean(w.get('topic')))}：{esc(clean(w.get('description')))}</li>" for w in warnings[:4])
    return f'<div class="warning-box"><h3>信息缺口与冲突</h3><ul>{items}</ul></div>'


def write_assets() -> None:
    (ASSET_DIR / "styles.css").write_text(STYLES, encoding="utf-8")
    (ASSET_DIR / "app.js").write_text(SCRIPT, encoding="utf-8")


def page_shell(title: str, body: str, depth: int) -> str:
    prefix = "./" if depth == 0 else "../" * depth
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{esc(title)}</title>
  <link rel="stylesheet" href="{prefix}assets/styles.css" />
</head>
<body>
{body}
<script src="{prefix}assets/app.js"></script>
</body>
</html>
"""


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


STYLES = r"""
:root {
  color-scheme: light;
  --bg: #f4f1ea;
  --paper: #fffdf8;
  --ink: #171613;
  --muted: #6d695f;
  --line: #d8d0c1;
  --soft: #ebe4d6;
  --wash: #ded4c2;
  --accent: #8a3f2b;
  --accent-dark: #3f5e58;
  --shadow: 0 18px 45px rgba(31, 27, 20, .09);
  --serif: "Noto Serif SC", "Source Han Serif SC", "Songti SC", SimSun, serif;
  --sans: "Noto Sans SC", "Microsoft YaHei", "PingFang SC", "Segoe UI", sans-serif;
}

* { box-sizing: border-box; }

html { scroll-behavior: smooth; }

body {
  margin: 0;
  background: var(--bg);
  color: var(--ink);
  font-family: var(--sans);
  line-height: 1.65;
  text-wrap: pretty;
}

a { color: inherit; }

img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
  background: var(--soft);
}

.site-header {
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 24px;
  min-height: 68px;
  padding: 0 clamp(18px, 4vw, 48px);
  border-bottom: 1px solid color-mix(in srgb, var(--line) 72%, transparent);
  background: color-mix(in srgb, var(--bg) 88%, transparent);
  backdrop-filter: blur(16px);
}

.brand {
  display: inline-grid;
  gap: 1px;
  text-decoration: none;
}

.brand span,
.eyebrow,
.section-number {
  color: var(--accent);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: .14em;
  text-transform: uppercase;
}

.brand strong {
  font-family: var(--serif);
  font-size: 18px;
  font-weight: 600;
}

.site-header nav {
  display: flex;
  gap: 18px;
  color: var(--muted);
  font-size: 14px;
}

.site-header nav a,
.back-link {
  text-decoration: none;
}

main {
  width: min(1440px, 100%);
  margin: 0 auto;
}

.hero {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(290px, .75fr);
  gap: clamp(32px, 6vw, 96px);
  align-items: end;
  min-height: calc(100vh - 68px);
  padding: clamp(48px, 8vw, 112px) clamp(18px, 5vw, 72px) clamp(32px, 5vw, 72px);
  border-bottom: 1px solid var(--line);
}

.hero h1,
.section-heading h2,
.library-head h2,
.about h2,
.detail h1,
.research-note h2 {
  font-family: var(--serif);
  font-weight: 600;
  letter-spacing: 0;
  line-height: 1.04;
}

.hero h1 {
  max-width: 930px;
  margin: 16px 0 24px;
  font-size: clamp(44px, 8vw, 116px);
}

.hero-copy > p:not(.eyebrow) {
  max-width: 760px;
  margin: 0;
  color: var(--muted);
  font-size: clamp(17px, 2vw, 22px);
}

code {
  padding: 1px 5px;
  background: var(--soft);
  border: 1px solid var(--line);
  border-radius: 4px;
}

.hero-search {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
  max-width: 760px;
  margin-top: 34px;
}

input,
select,
button {
  font: inherit;
}

input[type="search"],
select {
  min-height: 48px;
  border: 1px solid var(--line);
  border-radius: 4px;
  background: var(--paper);
  color: var(--ink);
}

input[type="search"] { padding: 0 14px; }
select { padding: 0 38px 0 12px; }

button {
  min-height: 48px;
  border: 1px solid var(--ink);
  border-radius: 4px;
  padding: 0 18px;
  background: var(--ink);
  color: var(--paper);
  cursor: pointer;
}

button:disabled {
  border-color: var(--line);
  background: var(--soft);
  color: var(--muted);
  cursor: not-allowed;
}

.hero-panel {
  display: grid;
  grid-template-columns: 1fr 1fr;
  border-top: 1px solid var(--ink);
  border-left: 1px solid var(--ink);
}

.hero-panel div {
  min-height: 132px;
  padding: 18px;
  border-right: 1px solid var(--ink);
  border-bottom: 1px solid var(--ink);
  background: color-mix(in srgb, var(--paper) 70%, transparent);
}

.hero-panel strong {
  display: block;
  font-family: var(--serif);
  font-size: clamp(28px, 4vw, 44px);
  line-height: 1;
}

.hero-panel span {
  display: block;
  margin-top: 16px;
  color: var(--muted);
  font-size: 13px;
}

.section-block {
  padding: clamp(56px, 7vw, 104px) clamp(18px, 5vw, 72px);
  border-bottom: 1px solid var(--line);
}

.section-heading {
  display: grid;
  grid-template-columns: minmax(0, 440px) minmax(0, 1fr);
  gap: 32px;
  align-items: end;
  margin-bottom: 28px;
}

.section-heading h2,
.library-head h2,
.about h2 {
  margin: 0;
  font-size: clamp(32px, 5vw, 64px);
}

.section-heading p:last-child,
.about p,
.muted {
  margin: 0;
  color: var(--muted);
}

.featured-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1px;
  background: var(--line);
  border: 1px solid var(--line);
}

.featured-card {
  min-height: 430px;
  background: var(--paper);
}

.featured-card a {
  display: grid;
  grid-template-rows: auto 1fr;
  height: 100%;
  text-decoration: none;
}

.featured-card img {
  aspect-ratio: 4 / 3;
  min-height: 0;
}

.featured-card a:not(:has(img)) {
  grid-template-rows: 1fr;
}

.featured-card div:last-child {
  padding: 18px;
}

.featured-card span,
.card-meta,
.source-list span,
.source-list em {
  color: var(--muted);
  font-size: 12px;
}

.featured-card h3,
.case-card h3,
.taxonomy-card h3,
.strategy-card h3 {
  margin: 8px 0;
  font-family: var(--serif);
  font-weight: 600;
  line-height: 1.15;
}

.featured-card h3 { font-size: clamp(22px, 3vw, 34px); }
.featured-card p,
.case-card p,
.taxonomy-card p,
.strategy-card p {
  margin: 0;
  color: var(--muted);
}

.taxonomy-grid {
  display: grid;
  grid-template-columns: 1.1fr 1fr .9fr;
  gap: 16px;
}

.taxonomy-card {
  min-height: 260px;
  border: 1px solid var(--line);
  background: var(--paper);
  padding: 22px;
}

.chip-row,
.tag-row,
.detail-tags,
.active-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chip,
.map-pin,
.tag-row span,
.detail-tags span,
.active-filters span {
  min-height: 34px;
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 6px 11px;
  background: var(--paper);
  color: var(--muted);
  font-size: 13px;
}

.chip.is-active,
.map-pin.is-active {
  border-color: var(--accent-dark);
  background: var(--accent-dark);
  color: var(--paper);
}

.map-surface {
  display: flex;
  min-height: 172px;
  align-items: center;
  align-content: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 10px;
  border: 1px solid var(--line);
  background:
    linear-gradient(90deg, transparent 49%, color-mix(in srgb, var(--line) 50%, transparent) 50%, transparent 51%),
    linear-gradient(0deg, transparent 49%, color-mix(in srgb, var(--line) 50%, transparent) 50%, transparent 51%),
    var(--bg);
}

.library-head {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: end;
  margin-bottom: 18px;
}

.sort-control {
  display: grid;
  gap: 6px;
  color: var(--muted);
  font-size: 13px;
}

.active-filters {
  min-height: 34px;
  margin-bottom: 18px;
}

.case-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
}

.case-card {
  border: 1px solid var(--line);
  background: var(--paper);
  min-width: 0;
  transition: transform .18s ease, box-shadow .18s ease;
}

.case-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow);
}

.case-card a {
  display: grid;
  grid-template-rows: auto 1fr;
  height: 100%;
  text-decoration: none;
}

.case-card a:not(:has(img)) {
  grid-template-rows: 1fr;
}

.case-card img {
  aspect-ratio: 16 / 10;
}

.case-card-body {
  display: grid;
  gap: 13px;
  padding: 16px;
  min-width: 0;
}

.card-meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.case-card h3 {
  margin: 0;
  font-size: 24px;
}

.case-card h3,
.case-card p,
.case-card dd,
.card-meta span,
.tag-row span,
.detail-title,
.strategy-card,
.note-list p {
  overflow-wrap: anywhere;
}

.case-card dl {
  display: grid;
  gap: 6px;
  margin: 0;
}

.case-card dl div,
.fact-strip div {
  display: grid;
  grid-template-columns: 68px 1fr;
  gap: 10px;
}

dt {
  color: var(--muted);
  font-size: 12px;
}

dd { margin: 0; }

.empty-state {
  margin-top: 18px;
  padding: 36px;
  border: 1px dashed var(--line);
  background: var(--paper);
}

.about {
  display: grid;
  grid-template-columns: minmax(0, .85fr) minmax(0, 1.15fr);
  gap: 36px;
  align-items: start;
}

.detail {
  width: min(1360px, 100%);
}

.detail-header {
  position: sticky;
}

.detail-hero {
  display: grid;
  grid-template-columns: minmax(0, .9fr) minmax(0, 1.1fr);
  gap: clamp(24px, 5vw, 72px);
  padding: clamp(34px, 6vw, 80px) clamp(18px, 5vw, 72px);
  border-bottom: 1px solid var(--line);
}

.back-link {
  display: inline-flex;
  margin-bottom: 28px;
  color: var(--accent);
  font-weight: 700;
}

.detail h1 {
  margin: 10px 0 20px;
  font-size: clamp(42px, 7vw, 88px);
}

.detail-title > p:not(.eyebrow) {
  color: var(--muted);
  font-size: 19px;
}

.quality-panel {
  margin-top: 26px;
  border: 1px solid var(--line);
  background: color-mix(in srgb, var(--paper) 72%, transparent);
  padding: 16px;
}

.quality-panel strong {
  display: block;
  margin-bottom: 10px;
  font-family: var(--serif);
  font-size: 18px;
}

.quality-panel dl {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px 16px;
  margin: 0;
}

.quality-panel p {
  margin: 12px 0 0;
  color: var(--muted);
  font-size: 14px;
}

.detail-media {
  min-height: 520px;
  margin: 0;
  border: 1px solid var(--line);
  background: var(--paper);
}

.text-media {
  display: grid;
  place-items: center;
  color: var(--muted);
  font-size: 13px;
  letter-spacing: .08em;
}

.detail-media figcaption,
.gallery-grid figcaption {
  display: grid;
  gap: 3px;
  padding: 10px;
  color: var(--muted);
  font-size: 12px;
}

.gallery-grid figcaption strong {
  color: var(--ink);
  font-size: 13px;
}

.fact-strip {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  border-bottom: 1px solid var(--line);
}

.fact-strip div {
  min-height: 110px;
  align-content: start;
  border-right: 1px solid var(--line);
  padding: 16px;
}

.reading-layout {
  display: grid;
  grid-template-columns: 260px minmax(0, 900px);
  gap: clamp(28px, 5vw, 72px);
  padding: clamp(42px, 7vw, 96px) clamp(18px, 5vw, 72px);
}

.research-nav {
  position: sticky;
  top: 92px;
  align-self: start;
  display: grid;
  gap: 10px;
  color: var(--muted);
}

.research-nav p {
  color: var(--ink);
  font-weight: 700;
}

.research-nav a {
  text-decoration: none;
}

.research-note {
  display: grid;
  gap: 54px;
}

.note-section {
  border-top: 1px solid var(--line);
  padding-top: 22px;
}

.research-note h2 {
  margin: 4px 0 18px;
  font-size: clamp(30px, 4vw, 54px);
}

.lead-copy {
  font-family: var(--serif);
  font-size: clamp(22px, 3vw, 32px);
  line-height: 1.45;
}

.strategy-grid,
.gallery-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.strategy-card,
.note-list p,
.structured-card,
.evidence-card,
.full-strategy,
.warning-box {
  border: 1px solid var(--line);
  background: var(--paper);
  padding: 18px;
}

.strategy-card span {
  color: var(--accent);
  font-weight: 700;
}

.note-list {
  display: grid;
  gap: 10px;
}

.full-strategy-list,
.evidence-grid {
  display: grid;
  gap: 14px;
}

.full-strategy {
  display: grid;
  gap: 12px;
}

.full-strategy > span {
  color: var(--accent);
  font-weight: 700;
  letter-spacing: .08em;
}

.full-strategy dl {
  display: grid;
  gap: 10px;
  margin: 0;
}

.full-strategy dl div {
  display: grid;
  grid-template-columns: 104px minmax(0, 1fr);
  gap: 16px;
  padding-top: 10px;
  border-top: 1px solid var(--line);
}

.evidence-card {
  display: grid;
  gap: 12px;
}

.evidence-card p,
.structured-card p {
  margin: 0;
}

.evidence-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.source-chip,
.evidence-meta span {
  display: inline-flex;
  width: fit-content;
  max-width: 100%;
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 3px 8px;
  color: var(--muted);
  font-size: 12px;
  overflow-wrap: anywhere;
  text-decoration: none;
}

.source-chip:hover {
  border-color: var(--accent);
  color: var(--accent);
  background: color-mix(in srgb, var(--accent) 8%, var(--paper));
}

.subsection-block {
  margin-top: 24px;
}

.subsection-block > h3,
.research-note h3 {
  font-family: var(--serif);
}

.compact-list {
  display: grid;
  gap: 8px;
  margin: 0;
  padding-left: 1.2em;
}

.data-table th {
  width: 160px;
  color: var(--muted);
  font-weight: 500;
}

.data-table th,
.data-table td {
  border: 1px solid var(--line);
  padding: 10px 12px;
  vertical-align: top;
}

.gallery-grid figure {
  margin: 0;
  border: 1px solid var(--line);
  background: var(--paper);
}

.gallery-grid img {
  aspect-ratio: 4 / 3;
}

.source-list {
  display: grid;
  gap: 0;
  padding: 0;
  list-style: none;
  border-top: 1px solid var(--line);
}

.source-list li {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid var(--line);
}

.source-list a {
  overflow-wrap: anywhere;
}

.source-list li:target,
.gallery-grid figure:target {
  outline: 2px solid var(--accent);
  outline-offset: 3px;
}

.source-list li p {
  grid-column: 1 / -1;
  margin: -4px 0 0;
  color: var(--muted);
  font-size: 13px;
}

.warning-box {
  margin-top: 18px;
}

.image-placeholder {
  display: grid;
  place-items: center;
  min-height: 220px;
  background: repeating-linear-gradient(135deg, var(--soft), var(--soft) 12px, var(--wash) 12px, var(--wash) 13px);
  color: var(--muted);
  font-size: 12px;
  letter-spacing: .12em;
}


/* Case deck presentation mode */
.case-deck {
  width: min(1440px, 100%);
  height: calc(100vh - 68px);
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto;
  gap: 10px;
  padding: clamp(16px, 2.4vw, 34px) clamp(14px, 3vw, 40px) 18px;
  overflow: hidden;
}

.deck-stage {
  position: relative;
  min-height: 0;
  height: 100%;
  border: 1px solid var(--line);
  background:
    linear-gradient(90deg, color-mix(in srgb, var(--line) 38%, transparent) 1px, transparent 1px),
    linear-gradient(0deg, color-mix(in srgb, var(--line) 30%, transparent) 1px, transparent 1px),
    color-mix(in srgb, var(--paper) 82%, var(--bg));
  background-size: 110px 110px;
  box-shadow: var(--shadow);
  overflow: hidden;
}

.deck-slide {
  position: absolute;
  inset: 0;
  opacity: 0;
  pointer-events: none;
  transform: translateX(18px) scale(.992);
  transition: opacity .28s ease, transform .32s ease;
  overflow: hidden;
}

.deck-slide.is-active {
  opacity: 1;
  pointer-events: auto;
  transform: translateX(0) scale(1);
}

.slide-grid {
  display: grid;
  grid-template-columns: minmax(0, .92fr) minmax(0, 1.08fr);
  gap: clamp(22px, 4vw, 62px);
  align-items: stretch;
  height: 100%;
  padding: clamp(26px, 4vw, 58px);
  min-height: 0;
  overflow: hidden;
}

.slide-copy {
  display: flex;
  min-width: 0;
  min-height: 0;
  flex-direction: column;
  justify-content: center;
  gap: 14px;
  overflow: auto;
  padding-right: 6px;
}

.slide-copy .back-link {
  width: fit-content;
  margin-bottom: clamp(14px, 3vh, 36px);
}

.slide-copy h1 {
  margin: 0;
  font-size: clamp(34px, 4.2vw, 66px);
  line-height: .98;
  overflow-wrap: anywhere;
}

.deck-slide:not(.is-cover) .slide-copy {
  justify-content: start;
}

.slide-lead {
  max-width: 780px;
  margin: 0;
  color: var(--muted);
  font-family: var(--serif);
  font-size: clamp(22px, 2.7vw, 36px);
  line-height: 1.42;
}

.slide-note,
.slide-points p {
  border-top: 1px solid var(--line);
  padding-top: 12px;
}

.slide-note h3 {
  margin: 0 0 6px;
  color: var(--accent);
  font-size: 14px;
  letter-spacing: .08em;
}

.slide-note p,
.slide-points p {
  margin: 0;
  color: var(--ink);
  font-size: clamp(16px, 1.35vw, 20px);
  line-height: 1.68;
}

.slide-points {
  display: grid;
  gap: 14px;
}

.slide-facts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1px;
  margin: 0;
  border: 1px solid var(--line);
  background: var(--line);
}

.slide-facts div {
  min-height: 112px;
  padding: 16px;
  background: color-mix(in srgb, var(--paper) 88%, transparent);
}

.slide-facts dt {
  margin-bottom: 8px;
}

.slide-facts dd {
  font-family: var(--serif);
  font-size: clamp(18px, 1.8vw, 26px);
  line-height: 1.28;
}

.slide-media {
  position: relative;
  min-height: 0;
  height: 100%;
  margin: 0;
  border: 1px solid var(--line);
  background: var(--soft);
  overflow: hidden;
}

.slide-media img {
  filter: saturate(.92) contrast(1.02);
}

.slide-media figcaption {
  position: absolute;
  right: 12px;
  bottom: 12px;
  left: 12px;
  padding: 9px 11px;
  background: color-mix(in srgb, var(--paper) 78%, transparent);
  backdrop-filter: blur(14px);
  color: var(--muted);
  font-size: 12px;
}

.is-cover .slide-grid {
  grid-template-columns: minmax(0, .82fr) minmax(0, 1.18fr);
}

.is-cover .hero-media {
  min-height: 0;
}

.is-scrollable .slide-grid {
  grid-template-columns: minmax(260px, .34fr) minmax(0, 1fr);
}

.is-scrollable .slide-copy {
  justify-content: start;
  overflow: auto;
  padding-right: 6px;
}

.is-scrollable .gallery-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-content: start;
}

.is-scrollable .source-list {
  margin: 0;
}

.is-text-only .slide-grid {
  grid-template-columns: minmax(0, 1fr);
}

.is-text-only .slide-copy {
  width: min(980px, 100%);
  justify-self: start;
}

.is-text-only .slide-copy h1 {
  max-width: 780px;
}

.is-text-only .markdown-table {
  max-width: 860px;
}

.is-appendix .compact-source-list {
  display: grid;
  gap: 12px;
  margin: 10px 0 0;
  padding: 0;
  list-style: none;
}

.compact-source-list li {
  display: grid;
  gap: 4px;
  border-top: 1px solid var(--line);
  padding-top: 12px;
}

.compact-source-list a {
  color: var(--ink);
  overflow-wrap: anywhere;
}

.compact-source-list span,
.source-lead {
  color: var(--muted);
}

.deck-controls {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr) 42px;
  gap: 10px;
  align-items: center;
  margin-top: 0;
}

.deck-arrow {
  display: grid;
  place-items: center;
  width: 42px;
  min-height: 38px;
  padding: 0;
  border-color: var(--line);
  background: var(--paper);
  color: var(--ink);
  font-size: 28px;
  line-height: 1;
}

.deck-progress {
  display: flex;
  gap: 4px;
  min-width: 0;
  overflow-x: auto;
  scrollbar-width: thin;
}

.deck-progress button {
  display: grid;
  flex: 1 0 28px;
  place-items: center;
  min-width: 0;
  max-width: 46px;
  min-height: 38px;
  border-color: var(--line);
  padding: 0 6px;
  background: var(--paper);
  color: var(--muted);
  text-align: center;
}

.deck-progress span {
  color: var(--accent);
  font-size: 11px;
  font-weight: 700;
}

.deck-progress button.is-active {
  border-color: var(--ink);
  background: var(--ink);
  color: var(--paper);
}

.deck-progress button.is-active span {
  color: var(--paper);
}

[hidden] { display: none !important; }

@media (max-width: 1040px) {
  .hero,
  .section-heading,
  .taxonomy-grid,
  .about,
  .detail-hero,
  .reading-layout {
    grid-template-columns: 1fr;
  }

  .case-grid,
  .featured-grid,
  .strategy-grid,
  .gallery-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .fact-strip {
    grid-template-columns: repeat(3, 1fr);
  }

  .research-nav {
    position: static;
    grid-template-columns: repeat(3, 1fr);
  }

  .slide-grid,
  .is-cover .slide-grid,
  .is-scrollable .slide-grid {
    grid-template-columns: 1fr;
    gap: 18px;
    overflow: auto;
  }

  .slide-media,
  .is-cover .hero-media {
    height: auto;
    aspect-ratio: 16 / 9;
    min-height: 280px;
  }
}

@media (max-width: 680px) {
  .site-header {
    align-items: start;
    flex-direction: column;
    padding-block: 12px;
  }

  .hero {
    min-height: auto;
  }

  .hero-search,
  .hero-panel,
  .case-grid,
  .featured-grid,
  .strategy-grid,
  .gallery-grid,
  .fact-strip,
  .research-nav {
    grid-template-columns: 1fr;
  }

  .library-head {
    align-items: stretch;
    flex-direction: column;
  }

  .detail-media {
    min-height: 300px;
  }

  .source-list li {
    grid-template-columns: 1fr;
  }

  .case-deck {
    padding-inline: 10px;
  }

  .slide-grid {
    padding: 18px;
  }

  .slide-copy h1 {
    font-size: clamp(28px, 9vw, 42px);
  }

  .slide-lead {
    font-size: 20px;
  }

  .deck-controls {
    grid-template-columns: 38px minmax(0, 1fr) 38px;
    gap: 8px;
  }

  .deck-progress button {
    flex-basis: 30px;
  }
}
"""


SCRIPT = r"""
(function () {
  const search = document.querySelector('#caseSearch');
  const cards = Array.from(document.querySelectorAll('.case-card'));
  const sortSelect = document.querySelector('#sortSelect');
  const empty = document.querySelector('#emptyState');
  const activeFilters = document.querySelector('#activeFilters');
  const filterButtons = Array.from(document.querySelectorAll('[data-filter]'));
  const grid = document.querySelector('#caseGrid');
  const state = { type: 'all', region: 'all', q: '', sort: 'year-desc' };

  function readParams() {
    const params = new URLSearchParams(window.location.search);
    state.q = params.get('q') || '';
    state.type = params.get('type') || 'all';
    state.region = params.get('region') || 'all';
    state.sort = params.get('sort') || 'year-desc';
    if (search) search.value = state.q;
    if (sortSelect) sortSelect.value = state.sort;
  }

  function writeParams() {
    const params = new URLSearchParams();
    if (state.q) params.set('q', state.q);
    if (state.type !== 'all') params.set('type', state.type);
    if (state.region !== 'all') params.set('region', state.region);
    if (state.sort !== 'year-desc') params.set('sort', state.sort);
    const next = params.toString() ? '?' + params.toString() : window.location.pathname;
    window.history.replaceState(null, '', next);
  }

  function sortCards(items) {
    return items.sort((a, b) => {
      if (state.sort === 'year-asc') return Number(a.dataset.year) - Number(b.dataset.year);
      if (state.sort === 'title-asc') return a.dataset.title.localeCompare(b.dataset.title);
      if (state.sort === 'architect-asc') return a.dataset.architect.localeCompare(b.dataset.architect);
      return Number(b.dataset.year) - Number(a.dataset.year);
    });
  }

  function paintButtons() {
    filterButtons.forEach((button) => {
      const key = button.dataset.filter;
      button.classList.toggle('is-active', state[key] === button.dataset.value);
    });
  }

  function paintFilterSummary(count) {
    if (!activeFilters) return;
    const chips = [];
    if (state.q) chips.push('搜索：' + state.q);
    if (state.type !== 'all') chips.push('类型：' + state.type);
    if (state.region !== 'all') chips.push('地区：' + state.region);
    chips.push(count + ' 个结果');
    activeFilters.innerHTML = chips.map((item) => '<span>' + item + '</span>').join('');
  }

  function apply() {
    const q = state.q.trim().toLowerCase();
    const visible = [];
    cards.forEach((card) => {
      const matchQuery = !q || (card.dataset.text || '').includes(q);
      const matchType = state.type === 'all' || card.dataset.type === state.type;
      const matchRegion = state.region === 'all' || card.dataset.region === state.region;
      const show = matchQuery && matchType && matchRegion;
      card.hidden = !show;
      if (show) visible.push(card);
    });
    sortCards(visible).forEach((card) => grid && grid.appendChild(card));
    if (empty) empty.hidden = visible.length !== 0;
    paintButtons();
    paintFilterSummary(visible.length);
    writeParams();
  }

  readParams();
  filterButtons.forEach((button) => {
    button.addEventListener('click', () => {
      state[button.dataset.filter] = button.dataset.value;
      apply();
    });
  });
  if (search) search.addEventListener('input', () => { state.q = search.value; apply(); });
  if (sortSelect) sortSelect.addEventListener('change', () => { state.sort = sortSelect.value; apply(); });
  if (cards.length) apply();
})();

(function () {
  const deck = document.querySelector('[data-case-deck]');
  if (!deck) return;

  const slides = Array.from(deck.querySelectorAll('[data-slide]'));
  const dots = Array.from(deck.querySelectorAll('[data-slide-target]'));
  const prev = deck.querySelector('[data-slide-prev]');
  const next = deck.querySelector('[data-slide-next]');
  const storageKey = 'caseDeck:' + window.location.pathname;
  let index = Number(window.localStorage.getItem(storageKey) || 0);

  function clamp(value) {
    return Math.max(0, Math.min(slides.length - 1, value));
  }

  function show(nextIndex) {
    index = clamp(nextIndex);
    slides.forEach((slide, slideIndex) => {
      slide.classList.toggle('is-active', slideIndex === index);
      slide.setAttribute('aria-hidden', slideIndex === index ? 'false' : 'true');
    });
    dots.forEach((dot, dotIndex) => {
      dot.classList.toggle('is-active', dotIndex === index);
      dot.setAttribute('aria-selected', dotIndex === index ? 'true' : 'false');
    });
    if (prev) prev.disabled = index === 0;
    if (next) next.disabled = index === slides.length - 1;
    window.localStorage.setItem(storageKey, String(index));
  }

  dots.forEach((dot) => {
    dot.addEventListener('click', () => show(Number(dot.dataset.slideTarget)));
  });
  if (prev) prev.addEventListener('click', () => show(index - 1));
  if (next) next.addEventListener('click', () => show(index + 1));
  window.addEventListener('keydown', (event) => {
    if (event.key === 'ArrowRight' || event.key === ' ') {
      event.preventDefault();
      show(index + 1);
    }
    if (event.key === 'ArrowLeft') {
      event.preventDefault();
      show(index - 1);
    }
  });

  show(index);
})();
"""


if __name__ == "__main__":
    raise SystemExit(main())
