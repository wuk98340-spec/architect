---
name: architectural-case-study
description: Generate concise, cited architecture case research packages from public web sources. Use when the user asks to research, organize, analyze, summarize, compare, or prepare a case study for an architecture project, architect, studio, building type, design strategy, static case-library website, or future architecture knowledge base/RAG workflow.
---

# Architectural Case Study

## Overview

Use this skill to turn public architecture sources into a reusable case research package. The default output is a quick card-level package in Chinese, with English project names and architectural terms preserved where useful.

This skill is for early-stage architecture case collection: project facts, concept summary, design strategies, spatial ideas, source links, and image links. Do not write a thesis-style literature review unless the user asks.

## Workflow

1. Clarify the target only if the prompt is ambiguous. Prefer the project name plus architect/studio when available.
2. Search public web sources in this priority order:
   - Official sources: architect/studio project pages, owner/institution pages, exhibition pages, award pages.
   - Architecture media: ArchDaily, Dezeen, Designboom, Divisare, World-Architects, The Architect's Newspaper, Architectural Record, Domus, Wallpaper.
   - General media: Wired, Architectural Digest, newspapers, magazines, local government or tourism pages.
   - Reference-only sources: Wikipedia, database mirrors, Pinterest, image aggregators, AI summaries, listicles.
3. Prefer verified facts from official sources. Use media sources for descriptions, interpretation, photographs, and critical context.
4. Record conflicts instead of smoothing them over. If year, location, status, area, or program differs across sources, state the conflict in `uncertain_or_conflicting_info`.
5. Create a folder under `case-packages/<slug>/` unless the user gives another location.
6. Produce both:
   - `case.md` for human reading and website copy drafting.
   - `case.json` for future static-site or RAG ingestion.
7. Run `scripts/validate_case_package.py <case-folder>` before finishing when a `case.json` exists.

## Output Rules

Read `references/case-package-template.md` before writing `case.md`.

Read `references/case-package-schema.json` before writing `case.json`. Follow the field names exactly. Use empty strings or empty arrays only when information was searched for but not found, and explain important gaps in `uncertain_or_conflicting_info`.

Read `references/source-quality.md` before assigning source levels or handling image links.

Write in Chinese by default. Keep proper nouns such as project names, studio names, material systems, awards, and key English concepts in English when translation would reduce precision.

Keep the style compact and case-library friendly: clear facts, short concept paragraphs, and direct strategy bullets. Use the BIG / PIXEL project-page style as a tone reference: concise project facts, visual/spatial concept first, then project meaning.

## Research Standards

- Do not download images by default. Collect image page URLs or direct image URLs only when clearly available, plus source and intended use.
- Do not treat a single reference-only source as enough for a key fact.
- Do not invent missing data such as area, budget, structural system, collaborators, or completion year.
- Distinguish project description from interpretation. Mark inferred design strategies as synthesis when not directly stated by a source.
- Keep citations close to claims in `case.md`, and preserve all source URLs in `case.json`.

## Validation

Run:

```bash
python scripts/validate_case_package.py case-packages/<slug>
```

If the system has no `python` command, use the available Python executable directly.

The validator checks required JSON fields, source levels, image-link fields, and whether at least one non-reference source exists.
