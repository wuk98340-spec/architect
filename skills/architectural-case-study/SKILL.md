---
name: architectural-case-study
description: Generate cited professional architecture case research packages from public web sources. Use when the user asks to research, organize, analyze, summarize, compare, or prepare a case study for an architecture project, architect, studio, building type, design strategy, static case-library website, course study, image-linked case archive, or future architecture knowledge base/RAG workflow.
---

# Architectural Case Study

## Overview

Use this skill to create a reusable architecture case research package in Chinese, preserving English project names, studio names, awards, and precise architectural terms where useful.

The default package contains `case.md` for reading and website copy, plus `case.json` for case-library or RAG ingestion. Treat the output as architecture case research, not a generic encyclopedia summary.

## Workflow

1. Create a folder under `case-packages/<slug>/` unless the user gives another location.
2. Run the Disambiguation Gate before writing a full package.
3. Search sources by the Level A-D priority in `references/source-quality.md`.
4. For Chinese architecture projects, run the gooood fallback in `references/source-quality.md` before concluding that no Level B source exists.
5. Identify `case_type` before analysis, then choose the strongest 3-5 architectural strategies using `references/architecture-analysis-taxonomy.md`.
6. Read `references/case-package-template.md` before writing `case.md`.
7. Read `references/case-package-schema.json` before writing `case.json`. Follow field names exactly.
8. Collect image links by default when images or drawings directly support the written analysis. Download images only when the user explicitly asks.
9. Run the quality self-check below before finishing.
10. Run `scripts/validate_case_package.py <case-folder>` when a `case.json` exists.

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

For gooood specifically, do not rely only on ordinary web search or the visible `?s=` search page. If `site:gooood.cn` searches do not find a likely article, use the gooood API fallback in `references/source-quality.md` before marking the project as missing from gooood.

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

## Image Workflow

Default mode: do not download images. Still collect image links when they strongly support text analysis, especially for site, plan, section, massing, facade, structure, material detail, concept, and circulation claims.

Enhanced mode: if the user explicitly asks to download images or organize an image package, create `images/` and download publicly accessible images when lawful and technically possible.

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

Do not download images from Pinterest, unsourced galleries, AI aggregation sites, or pages without usable image links. Do not describe unclear copyright as commercial permission. If download fails, keep the URL and failure reason.

## Output Rules

Write compact, case-library friendly Chinese. Keep claims close to citations in `case.md`, and preserve all source URLs in `case.json`.

In `case.md`, include relevant image links near the strategy, space, facade, or construction analysis they support, not only in the image index.

In `case.json`, use empty strings or empty arrays only when information was searched for but not found. Explain important gaps in `uncertain_or_conflicting_info` and `incomplete_reason`.

## Quality Self-Check

Before finishing, verify:

- Project identity is confirmed or ambiguity has been handled.
- `disambiguation_status`, `case_type`, and `information_confidence` are present.
- Sources have Level A-D labels.
- Core facts do not rely only on Level D.
- Facts, source quotes/paraphrases, and AI synthesis are clearly separated.
- The case has 3-5 real architectural strategies, each with evidence/source.
- The most valuable learning point is stated.
- Missing, uncertain, or conflicting information is recorded.
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
