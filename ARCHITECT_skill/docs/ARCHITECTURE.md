# Architectural Case Study Website Architecture

## System Overview

The website should wrap the existing case-study workflow rather than replace it. The current repository already has the durable domain model and quality controls:

- Skill instructions: `skills/architectural-case-study/SKILL.md`
- Source and analysis references: `skills/architectural-case-study/references/`
- Case package validator: `skills/architectural-case-study/scripts/validate_case_package.py`
- Validation plus quality wrapper: `skills/architectural-case-study/scripts/check_case_package.py`
- Quality scorer: `scripts/review_case_quality.py`
- Static site builder: `scripts/build_site.py`
- Canonical packages: `case-packages/<slug>/`

The future app should orchestrate these pieces through a backend, then present their outputs through a frontend.

## Canonical Data Contract

`case-packages/<slug>/` remains the source of truth.

Required files:

- `case.md`: readable professional case-study note.
- `case.json`: structured data that follows `case-package-schema.json`.

Optional folders:

- `images/`: local analysis-relevant images and drawings referenced by `case.md` and `case.json.image_metadata[]`.
- `sources/`: local PDFs or evidence files for PDF Source Mode.
- `revisions/`: local repair backups created before scoped repairs.

Generated or derived outputs:

- `quality-reports/<slug>-quality-report.md`
- `site/`
- Future API response JSON
- Future frontend view models

Derived outputs must not become the canonical case source.

## Recommended MVP Stack

Use a conservative local-first stack:

- Backend: Python with FastAPI.
- Frontend: React/Vite or Next.js.
- Case rendering: Markdown-to-HTML renderer that supports local image paths.
- Process orchestration: backend job runner that invokes existing Python scripts and delegates generation work to Codex/Agent workflow.

The exact dependency versions can be chosen during implementation. This document only fixes the system boundaries and data contract.

## Backend Responsibilities

The backend should expose local API endpoints for:

- Creating a generation request from user input.
- Returning disambiguation candidates.
- Accepting user confirmation.
- Starting generation after confirmation.
- Reporting job status and logs.
- Listing case packages.
- Reading a case package.
- Serving local images from `case-packages/<slug>/images/`.
- Running validation and quality scoring.

Generation should keep the existing Skill rules intact:

- Run disambiguation before full generation when identity is unclear.
- Preserve `case.md` and `case.json` synchronization.
- Use existing source-quality and analysis-taxonomy rules.
- Validate with `validate_case_package.py`.
- Score with `check_case_package.py` or `review_case_quality.py` when available.

## Frontend Responsibilities

The frontend should provide:

- Case query input.
- Disambiguation candidate table with confirm action.
- Generation progress view.
- Case library list with search/filter.
- Case detail view rendering `case.md`.
- Metadata panels from `case.json`: facts, source quality, images, uncertainty, incomplete reason, validation status.
- Clear blocked/error states for ambiguous identity, insufficient sources, validation failure, or generation failure.

The frontend should read through the backend API, not directly mutate case package files.

## API Shape Draft

These routes are a planning target, not a committed implementation:

- `POST /api/generation-requests`
- `GET /api/generation-requests/{id}`
- `POST /api/generation-requests/{id}/confirm-candidate`
- `POST /api/generation-requests/{id}/generate`
- `GET /api/cases`
- `GET /api/cases/{slug}`
- `GET /api/cases/{slug}/markdown`
- `GET /api/cases/{slug}/images/{path}`
- `POST /api/cases/{slug}/validate`
- `POST /api/cases/{slug}/quality-review`

API responses may normalize data for the UI, but must keep original `case.json` available for inspection.

## Data Flow

1. Frontend submits query.
2. Backend creates a generation job.
3. Agent workflow searches and disambiguates.
4. If ambiguous, backend stores candidates and waits for user confirmation.
5. After confirmation, Agent workflow writes `case-packages/<slug>/case.md`, `case.json`, and images.
6. Backend runs validation and quality scoring.
7. Frontend displays completed package or actionable failure state.

## Compatibility Rules

- Do not change `case-package-schema.json` unless a future task explicitly requests schema evolution.
- Do not add fields to `case.json`; the schema uses `additionalProperties: false`.
- Do not treat `site/` as source data. It is generated output.
- Do not commit `case-packages/`; it is intentionally ignored by `.gitignore`.
- Preserve existing scripts and Skill files unless a later implementation task explicitly targets them.
- Handle historical encoding issues defensively; new documents and new UI text should be normal UTF-8.

