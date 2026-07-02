---
name: architectural-case-study
description: Generate or locally refine cited professional architecture case research packages from public web sources, with concept-to-built analysis covering site, concept, spatial language, drawings, materials, tectonics, and built quality. Use when the user asks to search for, collect, research, organize, analyze, summarize, compare, prepare, revise, partially repair, or locally optimize architecture case studies, including Chinese requests such as 搜集建筑案例, 收集建筑案例, 整理建筑案例, 建筑案例分析, 案例调研, 建筑项目资料整理, 修改已生成案例, 局部优化章节, 重写策略, 重写定位, 替换单张图片, or case packages for an architecture project, architect, studio, building type, design strategy, course study, locally embedded image case archive, or structured reuse in a future architecture knowledge base/RAG workflow.
---

# Architectural Case Study

## Core Intent

Create or locally refine reusable architecture case research packages in Chinese, while preserving English project names, studio names, awards, and precise architectural terms where useful.

Treat the output as professional architecture case research, not an encyclopedia summary. The main argument should trace a project from diagnosis and positioning, through spatial/formal language, into material, tectonic, and built-quality decisions when reliable evidence allows.

The default package contains `case.md` for reading and study notes plus `case.json` for structured reuse. Prioritize the quality and evidence discipline of `case.md`, and keep `case.md`, `case.json`, sources, and images synchronized.

## Modes

- Use Full Generation for a new case package or substantial regeneration.
- Use PDF Source Mode when user-supplied PDFs are the evidence base. This changes source collection only; keep the same package structure, analysis frame, image rules, and validation requirements.
- Use Local Repair Mode when an existing package has `case.md` and `case.json` and the user asks to change only a chapter, strategy, field, evidence gap, image, caption, or metadata item.
- If the requested package, section, or image is unclear, inspect available case packages first; ask only when the target cannot be inferred.

## Required References

Load only the references needed for the active mode:

- Always read `references/source-quality.md` before collecting, classifying, or citing sources. It defines Level A-D sources, source sufficiency, PDF evidence handling, gooood / ArchDaily / 有方 handling, WeChat / Zhihu fallback, confidence wording, and image source rules.
- Always read `references/architecture-analysis-taxonomy.md` before analysis. Use it to identify `case_type`, choose the strongest 3-5 evidence-backed strategies, and frame the three-layer chain: Conceptual Exploration, Architectural Language Generation, and Construction Quality Control.
- Read `references/case-package-template.md` before writing or substantially rewriting `case.md`.
- Read `references/case-package-schema.json` before writing or substantially changing `case.json`. Follow field names exactly and do not invent schema fields unless the user explicitly asks for schema evolution.
- In Local Repair Mode, read `references/local-repair-workflow.md` before editing.

## Full Generation Workflow

1. Create `case-packages/<slug>/` unless the user gives another location.
2. Run the Disambiguation Gate before writing a full package.
3. Collect sources using `references/source-quality.md`; for PDF mode, work offline from PDFs unless the user asks for web supplementation.
4. Look beyond concept blurbs: search for site plans, floor plans, sections, elevations, diagrams, material notes, structure, construction process, detail drawings, climate response, and technical metrics.
5. Decide source sufficiency and confidence before drafting. Missing Level A is not automatic failure; weak or Level D-heavy evidence requires cautious or preliminary wording.
6. Identify `case_type`, then analyze the strongest evidence-backed concept-to-built chain rather than mechanically filling every possible subsection.
7. Write `case.md` from the template and `case.json` from the schema.
8. Create `images/` by default. Download or record analysis-relevant images/drawings when lawful and technically possible, and embed each useful downloaded image near the claim it supports.
9. Run validation and quality scoring before finishing.

## PDF Source Mode

Use PDF Source Mode when the user supplies PDFs and wants the package generated from them.

- Copy PDFs into `case-packages/<slug>/sources/` when creating a package.
- Record PDF sources with `source_kind`, `file_path`, and `page_count` when available.
- Set `source_mode` to `pdf` for PDF-only packages and `mixed` only when PDF and web/local non-PDF sources both support the package.
- Preserve page evidence in `evidence_spans[]` and cite pages close to claims in `case.md`, such as `来源明确：PDF《title》，p.12`.
- Do not turn the output into a PDF summary or page-by-page reading note.
- If PDF text, drawings, or technical evidence is thin, record the gap in `incomplete_reason`, `uncertain_or_conflicting_info`, and the relevant Markdown section.
- On Windows, avoid passing garbled non-ASCII PDF paths through shell commands; use Python `Path` discovery or copy to an ASCII path first.

## Local Repair Workflow

In Local Repair Mode:

1. Inspect the existing `case.md`, `case.json`, images, and the requested target.
2. Run `scripts/backup_case_package.py <case-folder> --label <repair-label>` before editing; include `--image <path>` when replacing an image.
3. Change only the requested scope, keeping Markdown, JSON, source IDs, image IDs, captions, relevance reasons, related sections, and image index rows synchronized.
4. Reuse existing sources when sufficient. Search only for new factual claims, image replacement, evidence weaknesses, or explicit stronger-source requests.
5. Validate after repair and report the validation result plus any quality-score change when available.

## Disambiguation Gate

Before full generation, decide whether the project identity is clear. Treat the target as ambiguous when names, phases, locations, translations, architects, completion status, or similar projects could point to multiple cases.

If ambiguous, do not generate the full package. Output a candidate table with project, location, architect/studio, year, type, main sources, confidence, and the question for the user. Continue only when one candidate is high confidence or the user confirms the target. Record the outcome in `case.json.disambiguation_status`.

## Writing And Evidence Rules

- Write compact, case-library friendly Chinese.
- Keep claims close to citations and preserve source URLs in `case.json`.
- Separate `来源明确`, `基于资料的归纳判断`, and `未检索到可靠资料`.
- Do not invent area, year, status, structure, materials, collaborators, design intent, construction details, technical metrics, or construction procedures.
- Do not force every case into the same headings or strategy set.
- If public evidence is thin, merge weak subsections into concise missing-information notes instead of repeating empty headings.
- Write design lessons as transferable methods, not generic inspiration.

## Image Rules

- Images are required by default unless the user explicitly asks for link-only or no-image output.
- Select images only when they support a written analysis claim; prioritize site, plan, section, circulation, massing, facade, structure, material detail, concept-generation, and user-experience evidence.
- Embed downloaded images in `case.md` near the relevant paragraph, strategy, or section using local relative paths such as `![caption](images/03_plan.jpg)`.
- Never leave downloaded images only in the image index, and never use prose placeholders such as `img1`, `img2`, or `相关图片：img1、img2`.
- If an image fails or should be skipped, keep the original URL near the relevant analysis, set `download_status` to `failed` or `skipped`, and explain `failure_reason`.
- Do not download from Pinterest, unsourced galleries, AI aggregation sites, or pages without usable image links. Treat downloads as research organization, not commercial rights clearance.

## Validation

Run validation whenever a `case.json` exists:

```bash
python skills/architectural-case-study/scripts/validate_case_package.py case-packages/<slug>
```

Prefer the bundled wrapper when available because it runs validation and the repository quality scorer together:

```bash
python skills/architectural-case-study/scripts/check_case_package.py case-packages/<slug> --output quality-reports/<slug>-quality-report.md
```

If `scripts/review_case_quality.py` reports `BLOCKED` or a score below 70, fix structural, source, strategy, image, or writing-depth issues before finishing unless the user explicitly asked for a rough draft.

Report validation status, quality score, main deductions, and any remaining evidence limits in the final response.
