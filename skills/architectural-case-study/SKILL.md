---
name: architectural-case-study
description: Generate cited professional architecture case research packages from public web sources, with concept-to-built analysis covering site, concept, spatial language, drawings, materials, tectonics, and built quality. Use when the user asks to search for, collect, research, organize, analyze, summarize, compare, or prepare architecture case studies, including Chinese requests such as 搜集建筑案例, 收集建筑案例, 整理建筑案例, 建筑案例分析, 案例调研, 建筑项目资料整理, or case packages for an architecture project, architect, studio, building type, design strategy, course study, locally embedded image case archive, static case-library website, or future architecture knowledge base/RAG workflow.
---

# Architectural Case Study

## Overview

Use this skill to create a reusable architecture case research package in Chinese, preserving English project names, studio names, awards, and precise architectural terms where useful.

Treat the output as architecture case research, not a generic encyclopedia summary. The writing goal is a professional "from concept to built work" study: trace how a project moves from diagnosis and positioning, through spatial/formal language, into material, tectonic, and built-quality decisions when reliable public evidence allows.

The default package contains `case.md` for reading and study notes, plus `case.json` for structured reuse. Prioritize the professional quality of `case.md` unless the user explicitly asks for website or RAG schema work.

## Workflow

1. Create a folder under `case-packages/<slug>/` unless the user gives another location.
2. Run the Disambiguation Gate before writing a full package.
3. Search sources by the Level A-D priority and Source Handling Order in `references/source-quality.md`.
4. For professional architecture media, run the source-specific handling for gooood, ArchDaily / ArchDaily China, and Archiposition / 有方 before concluding that no Level B source exists.
5. For supplementary Chinese commentary, use Sogou WeChat and Sogou Zhihu handling in `references/source-quality.md`; treat them as supporting sources, not substitutes for official or professional media. If no Level B professional architecture media is retained, this WeChat / Zhihu fallback is mandatory before generating the package.
6. Run the Source Sufficiency Gate in `references/source-quality.md` after searching, then choose formal generation, cautious generation, preliminary generation, or Disambiguation Gate.
7. During source collection, actively look beyond concept descriptions: site plans, floor plans, sections, elevations, diagrams, material notes, structure, construction process, detail drawings, climate response, and technical metrics. Do not stop at media introductions when drawings or construction-relevant evidence may exist.
8. Identify `case_type` before analysis, then use `references/architecture-analysis-taxonomy.md` to frame the project through three layers: Conceptual Exploration, Architectural Language Generation, and Construction Quality Control. Choose the strongest 3-5 evidence-backed strategies within those layers.
9. Read `references/case-package-template.md` before writing `case.md`.
10. Read `references/case-package-schema.json` before writing `case.json`. Follow field names exactly. Do not invent new schema fields unless the user explicitly asks for schema evolution.
11. Create `images/` by default and download publicly accessible, analysis-relevant images and drawings when lawful and technically possible. Before selecting each image, judge whether it directly supports a written analysis claim; do not include images that are only decorative, generic, or weakly related.
12. Run the Image Completion Gate below before finishing.
13. Run the quality self-check below before finishing.
14. Run `scripts/validate_case_package.py <case-folder>` when a `case.json` exists.

## Disambiguation Gate

Before generating a full case package, determine whether the project identity is clear.

Treat the target as ambiguous when any of these apply:

- Same or similar project names exist in different cities or countries.
- The project has phases, an extension, renovation, competition proposal, unbuilt version, or completed version.
- Chinese name, English name, and media translations differ.
- The same architect or studio has several similar projects.
- The user provides only a building name without architect/studio, location, year, or type.

If ambiguity exists, do not generate the full package yet. Output a candidate table and ask the user to confirm:

| Candidate project | Location | Architect / studio | Year | Type | Main sources | Confidence | Question for user |
| --- | --- | --- | --- | --- | --- | --- | --- |

Continue only when one candidate has high confidence or the user confirms the target. Record the result in `case.json.disambiguation_status`.

## Source Standards

Read `references/source-quality.md` before assigning source levels. Use:

- `level_a`: official and primary sources.
- `level_b`: high-quality architecture media.
- `level_c`: supplementary Chinese or local sources.
- `level_d`: reference-only sources.

Level A/B sources are preferred, but they are not a hard pass/fail requirement. Source quality controls confidence and wording:

- If Level A/B exists, use it for project identity, core facts, design intent, drawings, and image sources.
- If no Level A/B exists but several Level C sources corroborate one another, generate the package with medium or limited confidence and explain the limitation.
- If mainly Level D exists, generate only a preliminary package, mark low confidence, state the incomplete reason at the top, and avoid over-professionalized strategy claims.

Missing Level A sources alone must not make a case insufficient. Treat Level A as the preferred identity calibration source, then use the Source Sufficiency Gate to evaluate identity confirmation, independent source count, analysis coverage, and secondary-source risk. Record the result in `case.json.source_quality`.

For source handling, do not rely only on ordinary web search or the first visible search page. For gooood, use the API fallback in `references/source-quality.md` before marking the project as missing from gooood. For ArchDaily, 有方, WeChat, and Zhihu, use the source-specific query patterns, retention quotas, and confidence rules in `references/source-quality.md`. When no Level B source is retained, record the mandatory WeChat / Zhihu fallback outcome in `source_quality`, `manual_review_needed`, and `uncertain_or_conflicting_info`.

Do not invent area, year, status, structure, material, collaborators, or design intent. Record conflicts in `uncertain_or_conflicting_info`.

## Case Type Recognition

Set `case_type` before analysis. Use it to adjust emphasis:

- Cultural: publicness, urban interface, exhibition route, symbolic form.
- Education: learning spaces, open exchange, campus relation, flexible use.
- Hotel: arrival sequence, views, guestroom module, public areas, facade identity.
- Housing / apartment: unit logic, view, privacy, amenities, facade order.
- Commercial complex: circulation, tenant mix, interface, entrances, vertical transport, consumer path.
- Renovation: old-new relation, retained structure, material dialogue, historical memory.
- Rural / cultural tourism: local material, village fabric, operation, low-cost construction.
- Green building: climate response, energy, construction details, ecological systems.
- Other: identify the relevant dominant type and state why.

Do not force every case into the same headings or strategy set.

## Concept-To-Built Research Frame

Use the complete frame as a research compass, not a mandatory table to fill. `case.md` should expand only the parts supported by reliable sources, drawings, images, or clear project evidence. When public evidence is thin, merge weak subsections into a concise missing-information note instead of repeating `未检索到可靠资料` line by line.

- Conceptual Exploration: diagnosis, positioning, guiding strategies, imagery or diagrams, naming and expression.
- Architectural Language Generation: function, layout, circulation, massing, spatial sequence, envelope, openings, roof/base organization, place, atmosphere, light, material perception, and user experience.
- Construction Quality Control: structure, envelope, roof, platform, materials, craft, tectonic logic, physical performance, construction process, mockups, and quality-control measures.

Do not infer construction details, economic/technical metrics, structural systems, or construction procedures from generic architectural common sense. If no reliable source confirms them, state the limitation briefly.

## Image Workflow

Default mode: create `images/` inside the case package, download strongly relevant images when lawful and technically possible, and embed them in `case.md` with local relative paths such as `![caption](images/01_hero_exterior.jpg)`.

Select images only when they directly support the written analysis. Prioritize site, plan, section, circulation, massing, facade, structure, material detail, concept-generation, and user-experience claims over generic atmosphere images. For every selected image, write a `relevance_reason` in `case.json.image_metadata[]` that explains the exact claim or analysis move the image supports, for example: `用于验证屋顶平台与公共流线关系`.

Downloaded images must appear as Markdown image embeds near the relevant paragraph, strategy, or section in `case.md`. Do not leave downloaded images only in the image index, and do not replace them with placeholders such as `img1`, `img2`, or `相关图片：img1、img2`.

If an image cannot be downloaded, keep the original URL in `case.md` and `case.json`, set `download_status` to `failed`, and explain the failure in `failure_reason`. If an image is useful but should not be downloaded because of source quality, copyright ambiguity, or technical access limits, set `download_status` to `skipped` and keep the source URL. Failed or skipped image links must still appear near the analysis they support, with the failure or skip reason; do not hide them only in the image index.

Set `download_mode` to `completed` when all selected images are downloaded, `partial` when at least one selected image is failed or skipped, and `not_requested` only for legacy packages or when the user explicitly asks for link-only output.

Use these image types:

- `01_hero`: main view, aerial, exterior.
- `02_site`: location, master plan, site relation.
- `03_plan`: plan.
- `04_section`: section.
- `05_elevation`: elevation.
- `06_detail`: construction, detail, material.
- `07_concept`: concept diagram, generation logic.
- `08_interior`: interior space.
- `09_analysis`: images useful for secondary analysis.

Do not download images from Pinterest, unsourced galleries, AI aggregation sites, or pages without usable image links. Do not describe unclear copyright as commercial permission. Downloading images is research organization, not commercial rights clearance.

## Image Completion Gate

Before writing the final response, verify the case package has handled images.

- If the user did not explicitly ask for link-only or no-image output, do not set `download_mode` to `not_requested`.
- If reliable image sources exist, download at least one analysis-relevant image or drawing, record it in `case.json.image_metadata[]`, and embed it near the relevant analysis in `case.md`.
- If useful image sources exist but every download fails or should be skipped, set `download_mode` to `partial`, record each image as `failed` or `skipped`, keep the original source links near the relevant analysis in `case.md`, and explain the reason.
- If no reliable image or drawing source can be found after source-specific searching, set `download_mode` to `partial`, keep `image_metadata` empty, and state the image-source gap in both `incomplete_reason` and `uncertain_or_conflicting_info`.
- Treat a package with `download_mode: not_requested` as incomplete unless the user explicitly requested link-only or no-image output.

## Output Rules

Write compact, case-library friendly Chinese. Keep claims close to citations in `case.md`, and preserve all source URLs in `case.json`.

In `case.md`, distinguish evidence levels in the writing:

- `来源明确`: facts, intentions, drawings, or technical details stated by official sources, architects, awards, or professional media.
- `基于资料的归纳判断`: synthesis from plans, sections, photographs, and multiple descriptions.
- `未检索到可靠资料`: high-precision topics such as FAR, building density, structure, construction detail, or construction process that cannot be confirmed.

Do not write every possible subsection when evidence is weak. The professional quality comes from accurate selection, evidence discipline, and clear relationships between concept, space, and built result, not from longer headings.

In `case.md`, embed downloaded images near the strategy, space, facade, or construction analysis they support, not only in the image index. Use local relative paths under `images/`; fall back to the original URL only when download failed or was skipped. Never write only image IDs such as `相关图片：img1、img2`; convert every related downloaded image into `![说明](images/...)`.

In `case.json`, use empty strings or empty arrays only when information was searched for but not found. Explain important gaps in `uncertain_or_conflicting_info` and `incomplete_reason`.

## Quality Self-Check

Before finishing, verify:

- Project identity is confirmed or ambiguity has been handled.
- `disambiguation_status`, `case_type`, and `information_confidence` are present.
- `source_quality` is present, and its sufficiency status matches the source mix and analysis coverage.
- Sources have Level A-D labels.
- Missing Level A sources are not treated as automatic failure.
- Core facts do not rely only on Level D.
- Facts, source quotes/paraphrases, and AI synthesis are clearly separated.
- The case explains the strongest available concept-to-built chain: diagnosis/positioning, spatial/formal language, and construction/material quality when sources allow.
- The case has 3-5 real architectural strategies or methods, each with evidence/source.
- The design lessons are written as transferable design methods, not generic inspiration.
- Missing, uncertain, or conflicting information is recorded.
- Missing technical metrics, construction details, or construction process information are not guessed.
- Image metadata includes `relevance_reason` for every selected image.
- Downloaded images exist under `images/` and are embedded in `case.md` with Markdown image syntax near the relevant analysis.
- Failed or skipped images appear near the relevant analysis as source links with status and reason.
- `download_mode` is not `not_requested` unless the user explicitly requested link-only or no-image output.
- Image links have source, type, use, and copyright notes when relevant.
- Missing Level A/B is explained instead of treated as automatic failure.
- Only Level D sources trigger low confidence and preliminary wording.

If the self-check fails, state the incomplete reason at the start of the output and keep the package appropriately cautious.

## Validation

Run:

```bash
python scripts/validate_case_package.py case-packages/<slug>
```

If the system has no `python` command, use the available Python executable directly.
