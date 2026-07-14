# Codex Handoff: Architectural Case Study Website

## Current Objective

The repository is being prepared to evolve from a Codex Skill plus static local case library into a local frontend/backend website project.

The first implementation step is documentation only. Do not assume the app has been scaffolded yet.

## Read These First

1. `README.md`
2. `AGENT.md`
3. `skills/architectural-case-study/SKILL.md`
4. `skills/architectural-case-study/references/source-quality.md`
5. `skills/architectural-case-study/references/architecture-analysis-taxonomy.md`
6. `skills/architectural-case-study/references/case-package-template.md`
7. `skills/architectural-case-study/references/case-package-schema.json`
8. `docs/PRODUCT_SPEC.md`
9. `docs/ARCHITECTURE.md`
10. `docs/TASKS.md`

If working on local repair, also read `skills/architectural-case-study/references/local-repair-workflow.md`.

## Repository Facts

- `skills/architectural-case-study/` contains the project-local Skill.
- `case-packages/` contains canonical generated case packages.
- `case-packages/` is ignored by `.gitignore`; do not add it to Git.
- `scripts/build_site.py` generates `site/` from `case-packages/`.
- `site/` is generated output, not source data.
- `quality-reports/` contains generated quality reports.
- `output/` contains exported artifacts such as PDFs.
- `docs/` is for reusable workflow and project documentation.

## Existing Case Package Contract

Each canonical case package should use:

- `case.md`
- `case.json`
- Optional `images/`
- Optional `sources/`
- Optional `revisions/`

Do not change the existing `case.md` / `case.json` format for the website MVP.

`case.json` follows `skills/architectural-case-study/references/case-package-schema.json`. The schema disallows unknown fields, so UI-specific data should live in backend state, generated indexes, or API responses, not inside `case.json`.

## Existing Script Capabilities

- `skills/architectural-case-study/scripts/validate_case_package.py`
  validates package structure, source refs, image refs, image embedding policy, PDF evidence spans, and extended concept-to-built fields.
- `skills/architectural-case-study/scripts/check_case_package.py`
  runs validation and then the repository quality scorer when available.
- `skills/architectural-case-study/scripts/backup_case_package.py`
  backs up `case.md`, `case.json`, and optional images before local repair.
- `scripts/review_case_quality.py`
  scores package quality and writes Markdown or JSON reports.
- `scripts/build_site.py`
  reads `case-packages/` and writes the static `site/` directory.

## Skill Capability Boundary

The Skill currently supports:

- Full new case generation.
- PDF Source Mode.
- Local Repair Mode.
- Disambiguation before full generation.
- Level A-D source classification.
- Source sufficiency decisions.
- Concept-to-built architectural analysis.
- Image download/embedding rules.
- Validation and quality self-check before finishing.

The website should orchestrate these capabilities. It should not weaken source discipline or bypass disambiguation.

## MVP Product Flow

1. User enters an architecture case.
2. Backend/Agent disambiguates.
3. User confirms the intended candidate.
4. Backend/Agent generates `case.md`, `case.json`, and images in the existing format.
5. Backend validates and scores the package.
6. Frontend displays the case.

## Important Constraints

- Do not delete or rewrite the existing Skill.
- Do not modify `case.md` or `case.json` format unless the user explicitly asks for schema evolution.
- Do not add `case-packages/` to Git.
- Do not treat missing Level A sources as automatic failure; follow `source-quality.md`.
- Do not download images from weak or unsourced image sites.
- Do not infer construction, material, structure, area, or technical details without evidence.
- Do not hand-edit `site/` as durable source; edit source packages or build scripts, then rebuild when appropriate.

## Known Issues And Cautions

- Some historical Chinese text in repository files and generated site output appears garbled. New files should be written as normal UTF-8.
- Some generated/static files may already be modified in the working tree. Check `git status --short --branch` before editing and do not revert unrelated work.
- Historical packages may vary in image completeness and quality. The backend should surface validation status instead of assuming every package is clean.
- The current static site is useful as a reference, but the future app should be planned around canonical packages and backend APIs.

## Suggested Next Step

Implement Phase 1 from `docs/TASKS.md`: scaffold a read-only backend that lists existing case packages, reads `case.md` and `case.json`, serves local images, and reports validation state without modifying package files.

