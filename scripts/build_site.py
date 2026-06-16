#!/usr/bin/env python3
"""Build a local static architecture case library from case-packages."""

from __future__ import annotations

import html
import json
import re
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CASE_ROOT = ROOT / "case-packages"
SITE_ROOT = ROOT / "site"
ASSET_DIR = SITE_ROOT / "assets"
CASE_SITE_DIR = SITE_ROOT / "cases"


def main() -> int:
    cases = load_cases()
    if not cases:
        raise SystemExit("No case packages found.")

    if SITE_ROOT.exists():
        shutil.rmtree(SITE_ROOT)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    CASE_SITE_DIR.mkdir(parents=True, exist_ok=True)

    write_assets()
    for case in cases:
        build_case_page(case)
    write_index(cases)
    return 0


def load_cases() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for folder in sorted(CASE_ROOT.iterdir()):
        if not folder.is_dir():
            continue
        md_path = folder / "case.md"
        json_path = folder / "case.json"
        if not md_path.exists() or not json_path.exists():
            continue
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}

        slug = folder.name
        title = str(data.get("project_name") or first_markdown_title(md_path) or slug)
        summary = str(data.get("one_sentence_summary") or "").strip()
        if not summary:
            summary = extract_first_paragraph(md_path)

        items.append(
            {
                "slug": slug,
                "folder": folder,
                "md_path": md_path,
                "json_path": json_path,
                "data": data,
                "title": title,
                "summary": summary,
                "architects": normalize_join(data.get("architects")),
                "location": str(data.get("location") or "未记录"),
                "year": str(data.get("year") or "未记录"),
                "case_type": str(data.get("case_type") or data.get("program") or "未分类"),
                "confidence": str(data.get("information_confidence") or "unknown"),
                "has_images": (folder / "images").exists() and any((folder / "images").iterdir()),
                "source_count": len(data.get("sources", [])) if isinstance(data.get("sources"), list) else 0,
                "image_count": len(data.get("image_metadata", []))
                if isinstance(data.get("image_metadata"), list)
                else count_markdown_images(md_path),
            }
        )
    return sorted(items, key=lambda item: (item["year"], item["title"]), reverse=True)


def build_case_page(case: dict[str, Any]) -> None:
    out_dir = CASE_SITE_DIR / case["slug"]
    out_dir.mkdir(parents=True, exist_ok=True)

    image_dir = case["folder"] / "images"
    if image_dir.exists():
        shutil.copytree(image_dir, out_dir / "images", dirs_exist_ok=True)

    markdown = case["md_path"].read_text(encoding="utf-8")
    body, toc = markdown_to_html(markdown)
    data = case["data"]

    meta_rows = [
        ("建筑师", case["architects"]),
        ("地点", case["location"]),
        ("年份", case["year"]),
        ("类型", case["case_type"]),
        ("可信度", case["confidence"]),
        ("来源", f"{case['source_count']} 个"),
        ("图片", f"{case['image_count']} 张"),
    ]
    meta_html = "".join(
        f"<div><dt>{escape(label)}</dt><dd>{escape(value)}</dd></div>" for label, value in meta_rows
    )

    source_html = render_source_panel(data)
    toc_html = render_toc(toc)
    html_text = page_shell(
        title=case["title"],
        body=f"""
        <div class="case-layout">
          <aside class="case-aside">
            <a class="back-link" href="../../index.html">← 返回案例库</a>
            <dl class="meta-list">{meta_html}</dl>
            {toc_html}
          </aside>
          <main class="case-article">
            <div class="case-kicker">建筑案例研究</div>
            {body}
            {source_html}
          </main>
        </div>
        """,
        depth=2,
    )
    (out_dir / "index.html").write_text(html_text, encoding="utf-8")


def write_index(cases: list[dict[str, Any]]) -> None:
    cards = []
    type_options = sorted({case["case_type"] for case in cases if case["case_type"]})
    for case in cases:
        image_badge = "有图像" if case["has_images"] else "无本地图像"
        cards.append(
            f"""
            <article class="case-card" data-type="{escape(case['case_type'])}" data-text="{escape(search_text(case))}">
              <a href="cases/{escape(case['slug'])}/index.html">
                <div class="card-topline">
                  <span>{escape(case['year'])}</span>
                  <span>{escape(case['confidence'])}</span>
                </div>
                <h2>{escape(case['title'])}</h2>
                <p>{escape(case['summary'])}</p>
                <dl>
                  <div><dt>建筑师</dt><dd>{escape(case['architects'])}</dd></div>
                  <div><dt>地点</dt><dd>{escape(case['location'])}</dd></div>
                </dl>
                <div class="card-tags">
                  <span>{escape(case['case_type'])}</span>
                  <span>{image_badge}</span>
                  <span>{case['source_count']} 来源</span>
                </div>
              </a>
            </article>
            """
        )

    filter_buttons = ['<button class="filter active" data-type="all">全部</button>']
    filter_buttons.extend(
        f'<button class="filter" data-type="{escape(item)}">{escape(short_label(item))}</button>'
        for item in type_options
    )

    body = f"""
    <main class="home">
      <section class="home-header">
        <p class="eyebrow">ARCHITECTURE CASE LIBRARY</p>
        <h1>建筑案例库</h1>
        <p class="home-intro">把本地 Markdown 案例整理成可浏览、可复习、可持续扩展的静态资料库。</p>
        <div class="home-stats">
          <span>{len(cases)} 个案例</span>
          <span>{sum(case['image_count'] for case in cases)} 张图片 / 图纸记录</span>
          <span>{sum(case['source_count'] for case in cases)} 条来源</span>
        </div>
      </section>
      <section class="toolbar" aria-label="案例筛选">
        <input id="caseSearch" type="search" placeholder="搜索项目、地点、建筑师或关键词" />
        <div class="filters">{"".join(filter_buttons)}</div>
      </section>
      <section id="caseGrid" class="case-grid">{"".join(cards)}</section>
      <p id="emptyState" class="empty-state" hidden>没有匹配的案例。</p>
    </main>
    """
    (SITE_ROOT / "index.html").write_text(page_shell("建筑案例库", body, depth=0), encoding="utf-8")


def write_assets() -> None:
    (ASSET_DIR / "styles.css").write_text(STYLES, encoding="utf-8")
    (ASSET_DIR / "app.js").write_text(SCRIPT, encoding="utf-8")


def markdown_to_html(markdown: str) -> tuple[str, list[dict[str, str]]]:
    lines = markdown.splitlines()
    parts: list[str] = []
    toc: list[dict[str, str]] = []
    paragraph: list[str] = []
    list_items: list[str] = []
    blockquote: list[str] = []
    index = 0

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            text = " ".join(item.strip() for item in paragraph).strip()
            rendered = inline_markdown(text)
            if rendered.startswith("<figure>") and rendered.endswith("</figure>"):
                parts.append(rendered)
            elif "<figure>" in rendered:
                parts.append(f'<div class="media-note">{rendered}</div>')
            else:
                parts.append(f"<p>{rendered}</p>")
            paragraph = []

    def flush_list() -> None:
        nonlocal list_items
        if list_items:
            parts.append("<ul>" + "".join(f"<li>{inline_markdown(item)}</li>" for item in list_items) + "</ul>")
            list_items = []

    def flush_blockquote() -> None:
        nonlocal blockquote
        if blockquote:
            text = " ".join(item.strip() for item in blockquote).strip()
            parts.append(f"<blockquote>{inline_markdown(text)}</blockquote>")
            blockquote = []

    def flush_all() -> None:
        flush_paragraph()
        flush_list()
        flush_blockquote()

    while index < len(lines):
        line = lines[index].rstrip()
        stripped = line.strip()
        if not stripped:
            flush_all()
            index += 1
            continue

        if stripped.startswith("|") and index + 1 < len(lines) and is_table_separator(lines[index + 1]):
            flush_all()
            table_lines = [stripped, lines[index + 1].strip()]
            index += 2
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index].strip())
                index += 1
            parts.append(render_table(table_lines))
            continue

        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading:
            flush_all()
            level = len(heading.group(1))
            text = heading.group(2).strip()
            anchor = slugify(text)
            parts.append(f'<h{level} id="{anchor}">{inline_markdown(text)}</h{level}>')
            if 1 < level <= 3:
                toc.append({"level": str(level), "text": strip_markdown(text), "anchor": anchor})
            index += 1
            continue

        if stripped.startswith(">"):
            flush_paragraph()
            flush_list()
            blockquote.append(stripped.lstrip(">").strip())
            index += 1
            continue

        if re.match(r"^[-*]\s+", stripped):
            flush_paragraph()
            flush_blockquote()
            list_items.append(re.sub(r"^[-*]\s+", "", stripped))
            index += 1
            continue

        if re.match(r"^\d+\.\s+", stripped):
            flush_paragraph()
            flush_blockquote()
            list_items.append(re.sub(r"^\d+\.\s+", "", stripped))
            index += 1
            continue

        flush_list()
        flush_blockquote()
        paragraph.append(stripped)
        index += 1

    flush_all()
    return "\n".join(parts), toc


def render_table(lines: list[str]) -> str:
    rows = [split_table_row(line) for line in lines]
    headers = rows[0]
    body_rows = rows[2:]
    thead = "".join(f"<th>{inline_markdown(cell)}</th>" for cell in headers)
    tbody = "".join(
        "<tr>" + "".join(f"<td>{inline_markdown(cell)}</td>" for cell in row) + "</tr>" for row in body_rows
    )
    return f'<div class="table-wrap"><table><thead><tr>{thead}</tr></thead><tbody>{tbody}</tbody></table></div>'


def split_table_row(line: str) -> list[str]:
    content = line.strip().strip("|")
    return [cell.strip() for cell in content.split("|")]


def is_table_separator(line: str) -> bool:
    return bool(re.match(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$", line))


def inline_markdown(text: str) -> str:
    placeholders: list[str] = []

    def store(value: str) -> str:
        placeholders.append(value)
        return f"\u0000{len(placeholders) - 1}\u0000"

    text = re.sub(
        r"!\[([^\]]*)\]\(([^)]+)\)",
        lambda m: store(
            f'<figure><img src="{escape(rewrite_image_src(m.group(2).strip()))}" alt="{escape(m.group(1))}" loading="lazy" />'
            f"<figcaption>{escape(m.group(1))}</figcaption></figure>"
        ),
        text,
    )
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda m: store(f'<a href="{escape(m.group(2).strip())}">{escape(m.group(1))}</a>'),
        text,
    )
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    for i, value in enumerate(placeholders):
        text = text.replace(f"\u0000{i}\u0000", value)
    return text


def rewrite_image_src(src: str) -> str:
    if src.startswith(("http://", "https://", "/")):
        return src
    return src if src.startswith("./") else f"./{src}"


def page_shell(title: str, body: str, depth: int) -> str:
    prefix = "./" if depth == 0 else "../" * depth
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape(title)}</title>
  <link rel="stylesheet" href="{prefix}assets/styles.css" />
</head>
<body>
{body}
<script src="{prefix}assets/app.js"></script>
</body>
</html>
"""


def render_toc(toc: list[dict[str, str]]) -> str:
    if not toc:
        return ""
    links = "".join(
        f'<a class="toc-level-{item["level"]}" href="#{item["anchor"]}">{escape(item["text"])}</a>' for item in toc
    )
    return f'<nav class="toc" aria-label="本文目录"><h2>目录</h2>{links}</nav>'


def render_source_panel(data: dict[str, Any]) -> str:
    sources = data.get("sources")
    if not isinstance(sources, list) or not sources:
        return ""
    items = []
    for source in sources:
        if not isinstance(source, dict):
            continue
        title = escape(str(source.get("title") or source.get("url") or "来源"))
        url = escape(str(source.get("url") or "#"))
        level = escape(str(source.get("source_level") or ""))
        publisher = escape(str(source.get("publisher") or ""))
        items.append(f'<li><a href="{url}">{title}</a><span>{level}</span><em>{publisher}</em></li>')
    return f'<section class="source-panel"><h2>来源</h2><ul>{"".join(items)}</ul></section>'


def first_markdown_title(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# "):
            return strip_markdown(line[2:].strip())
    return ""


def extract_first_paragraph(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith(("#", "|", "!", "-", ">")):
            return strip_markdown(stripped)[:180]
    return ""


def count_markdown_images(path: Path) -> int:
    return len(re.findall(r"!\[[^\]]*\]\([^)]+\)", path.read_text(encoding="utf-8")))


def normalize_join(value: Any) -> str:
    if isinstance(value, list):
        return " / ".join(str(item) for item in value if str(item).strip()) or "未记录"
    if value:
        return str(value)
    return "未记录"


def search_text(case: dict[str, Any]) -> str:
    return " ".join(
        [case["title"], case["summary"], case["architects"], case["location"], case["year"], case["case_type"]]
    ).lower()


def short_label(value: str) -> str:
    if len(value) <= 18:
        return value
    return value[:18] + "..."


def slugify(value: str) -> str:
    base = re.sub(r"<[^>]+>", "", value).lower()
    base = re.sub(r"[^\w\u4e00-\u9fff]+", "-", base, flags=re.UNICODE).strip("-")
    return base or "section"


def strip_markdown(value: str) -> str:
    value = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", value)
    value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    value = value.replace("`", "").replace("*", "")
    return value


def escape(value: Any) -> str:
    return html.escape(str(value), quote=True)


STYLES = r"""
:root {
  color-scheme: light;
  --bg: #f7f7f4;
  --paper: #ffffff;
  --ink: #20211f;
  --muted: #646861;
  --line: #deded8;
  --soft: #eeeee8;
  --accent: #2f6f73;
  --accent-2: #9f4f35;
  --shadow: 0 16px 40px rgba(32, 33, 31, 0.08);
}

* { box-sizing: border-box; }

html { scroll-behavior: smooth; }

body {
  margin: 0;
  font-family: "Inter", "Segoe UI", "Microsoft YaHei", "PingFang SC", Arial, sans-serif;
  color: var(--ink);
  background: var(--bg);
  line-height: 1.65;
}

a { color: inherit; }

.home {
  width: min(1180px, calc(100% - 32px));
  margin: 0 auto;
  padding: 48px 0 72px;
}

.home-header {
  border-bottom: 1px solid var(--line);
  padding-bottom: 28px;
}

.eyebrow,
.case-kicker {
  margin: 0 0 8px;
  color: var(--accent);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: .08em;
}

h1 {
  margin: 0 0 12px;
  font-size: clamp(34px, 5vw, 64px);
  line-height: 1.05;
  letter-spacing: 0;
}

.home-intro {
  max-width: 680px;
  margin: 0;
  color: var(--muted);
  font-size: 18px;
}

.home-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 22px;
}

.home-stats span,
.card-tags span,
.source-panel li span {
  border: 1px solid var(--line);
  background: var(--soft);
  padding: 4px 9px;
  border-radius: 999px;
  color: var(--muted);
  font-size: 13px;
}

.toolbar {
  position: sticky;
  top: 0;
  z-index: 5;
  display: grid;
  grid-template-columns: minmax(220px, 360px) 1fr;
  gap: 16px;
  align-items: start;
  padding: 18px 0;
  background: color-mix(in srgb, var(--bg) 92%, transparent);
  backdrop-filter: blur(12px);
}

input[type="search"] {
  width: 100%;
  min-height: 42px;
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 0 12px;
  font: inherit;
  background: var(--paper);
}

.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.filter {
  min-height: 36px;
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 0 12px;
  background: var(--paper);
  color: var(--muted);
  cursor: pointer;
}

.filter.active {
  background: var(--accent);
  border-color: var(--accent);
  color: white;
}

.case-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px;
}

.case-card {
  min-height: 320px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--paper);
  box-shadow: var(--shadow);
}

.case-card a {
  display: flex;
  min-height: 100%;
  flex-direction: column;
  padding: 18px;
  text-decoration: none;
}

.card-topline {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  color: var(--accent-2);
  font-size: 13px;
  font-weight: 700;
}

.case-card h2 {
  margin: 18px 0 10px;
  font-size: 22px;
  line-height: 1.25;
}

.case-card p {
  margin: 0 0 18px;
  color: var(--muted);
}

.case-card dl,
.meta-list {
  display: grid;
  gap: 8px;
  margin: auto 0 16px;
}

.case-card dl div,
.meta-list div {
  display: grid;
  grid-template-columns: 64px 1fr;
  gap: 10px;
}

dt {
  color: var(--muted);
  font-size: 13px;
}

dd { margin: 0; }

.card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.empty-state {
  padding: 32px;
  border: 1px dashed var(--line);
  border-radius: 8px;
  text-align: center;
  color: var(--muted);
}

.case-layout {
  display: grid;
  grid-template-columns: 280px minmax(0, 860px);
  gap: 42px;
  width: min(1220px, calc(100% - 32px));
  margin: 0 auto;
  padding: 32px 0 72px;
}

.case-aside {
  position: sticky;
  top: 24px;
  align-self: start;
  max-height: calc(100vh - 48px);
  overflow: auto;
}

.back-link {
  display: inline-flex;
  margin-bottom: 22px;
  color: var(--accent);
  text-decoration: none;
  font-weight: 700;
}

.meta-list {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 16px;
  background: var(--paper);
}

.toc {
  margin-top: 16px;
  border-left: 2px solid var(--line);
  padding-left: 14px;
}

.toc h2 {
  margin: 0 0 8px;
  font-size: 14px;
  color: var(--muted);
}

.toc a {
  display: block;
  margin: 7px 0;
  color: var(--muted);
  text-decoration: none;
  font-size: 14px;
  line-height: 1.35;
}

.toc-level-3 { padding-left: 12px; }

.case-article {
  min-width: 0;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--paper);
  padding: clamp(20px, 5vw, 56px);
  box-shadow: var(--shadow);
}

.case-article h1 {
  font-size: clamp(30px, 4vw, 52px);
  border-bottom: 1px solid var(--line);
  padding-bottom: 18px;
}

.case-article h2 {
  margin-top: 42px;
  padding-top: 18px;
  border-top: 1px solid var(--line);
  font-size: 26px;
}

.case-article h3 {
  margin-top: 28px;
  font-size: 20px;
}

.case-article p,
.case-article li {
  font-size: 16px;
}

blockquote {
  margin: 20px 0;
  border-left: 4px solid var(--accent);
  padding: 10px 16px;
  background: var(--soft);
  color: var(--muted);
}

.table-wrap {
  width: 100%;
  overflow-x: auto;
  margin: 18px 0;
}

table {
  width: 100%;
  border-collapse: collapse;
  min-width: 620px;
}

th,
td {
  border: 1px solid var(--line);
  padding: 8px 10px;
  text-align: left;
  vertical-align: top;
}

th { background: var(--soft); }

figure {
  margin: 22px 0;
}

.media-note {
  margin: 22px 0;
}

.media-note figure {
  margin-bottom: 8px;
}

img {
  display: block;
  width: 100%;
  height: auto;
  border-radius: 6px;
  border: 1px solid var(--line);
  background: var(--soft);
}

figcaption {
  margin-top: 7px;
  color: var(--muted);
  font-size: 13px;
}

code {
  background: var(--soft);
  border-radius: 4px;
  padding: 1px 5px;
}

.source-panel {
  margin-top: 44px;
  border-top: 1px solid var(--line);
  padding-top: 18px;
}

.source-panel ul {
  list-style: none;
  padding: 0;
}

.source-panel li {
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: 10px;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid var(--line);
}

.source-panel em {
  color: var(--muted);
  font-style: normal;
  font-size: 13px;
}

@media (max-width: 860px) {
  .toolbar,
  .case-layout {
    grid-template-columns: 1fr;
  }

  .case-aside {
    position: static;
    max-height: none;
  }

  .toc {
    display: none;
  }

  .case-article {
    padding: 20px;
  }

  .source-panel li {
    grid-template-columns: 1fr;
  }
}
"""


SCRIPT = r"""
(function () {
  const search = document.querySelector('#caseSearch');
  const cards = Array.from(document.querySelectorAll('.case-card'));
  const filters = Array.from(document.querySelectorAll('.filter'));
  const empty = document.querySelector('#emptyState');
  let activeType = 'all';

  function applyFilters() {
    const query = search ? search.value.trim().toLowerCase() : '';
    let visible = 0;
    cards.forEach((card) => {
      const matchType = activeType === 'all' || card.dataset.type === activeType;
      const matchText = !query || (card.dataset.text || '').includes(query);
      const show = matchType && matchText;
      card.hidden = !show;
      if (show) visible += 1;
    });
    if (empty) empty.hidden = visible !== 0;
  }

  filters.forEach((button) => {
    button.addEventListener('click', () => {
      activeType = button.dataset.type || 'all';
      filters.forEach((item) => item.classList.toggle('active', item === button));
      applyFilters();
    });
  });

  if (search) search.addEventListener('input', applyFilters);
})();
"""


if __name__ == "__main__":
    raise SystemExit(main())
