# Architectural Case Study Website Product Spec

## Product Goal

Build a local web product around the existing `architectural-case-study` workflow so users can generate, review, and browse professional architecture case-study packages without needing to remember Codex prompt details.

The product should preserve the current research standard: Chinese professional case analysis, clear source discipline, disambiguation before generation, synchronized `case.md` and `case.json`, and analysis-relevant images embedded near the claims they support.

## MVP

The MVP flow is:

1. User enters an architecture case query, such as a building name, architect, city, year, or short brief.
2. Backend/Agent runs the existing disambiguation gate and returns candidate projects when the target is not clear.
3. User confirms one candidate or edits the query.
4. Backend/Agent generates the canonical package files: `case.md`, `case.json`, and optional `images/` / `sources/`.
5. Backend validates the package and records validation/quality status.
6. Frontend displays the generated case as a readable case page, with metadata, sources, images, and evidence limitations.

## Primary Users

- Architecture students collecting case-study references.
- Designers and researchers building a reusable architecture case library.
- Codex agents continuing case generation, repair, validation, and site/app development across separate contexts.

## Core User Stories

- As a user, I can submit a building case query and see whether the project identity is clear.
- As a user, I can choose from disambiguation candidates before any full package is generated.
- As a user, I can track generation state: searching, disambiguating, writing, validating, scoring, completed, or failed.
- As a user, I can open a completed case and read `case.md` with images rendered inline.
- As a user, I can inspect structured facts, source quality, image metadata, incomplete reasons, and uncertainty notes from `case.json`.
- As a future Codex agent, I can continue development from repository documentation rather than relying on chat history.

## Stable Output Contract

Do not redesign the case package format for the MVP.

The canonical output remains:

- `case-packages/<slug>/case.md`
- `case-packages/<slug>/case.json`
- `case-packages/<slug>/images/`
- Optional `case-packages/<slug>/sources/`
- Optional `quality-reports/<slug>-quality-report.md`

The website may create indexes, API responses, generated HTML, or UI-specific view models, but those must be derived from the canonical case package. `case.json` field names and validation rules remain controlled by `skills/architectural-case-study/references/case-package-schema.json` and `validate_case_package.py`.

## In Scope For MVP

- Case query submission.
- Disambiguation candidate display and confirmation.
- Generation orchestration through the existing Skill workflow.
- Case package validation and quality scoring.
- Case list and detail views.
- Local image rendering from `images/`.
- Source, confidence, and incomplete-information display.
- Clear failed/blocked states when sources, validation, or generation are insufficient.

## Out Of Scope For MVP

- Changing the `case.md` or `case.json` format.
- Replacing the existing Skill with a new generation system.
- Adding case packages to Git.
- Multi-user authentication, cloud deployment, billing, or public publishing.
- Full CMS editing workflows.
- Commercial image-rights clearance.
- Large-scale RAG, vector search, or knowledge graph features.

## Success Criteria

- A user can complete the full MVP flow from query to displayed case without manually opening the filesystem.
- Generated packages still pass `validate_case_package.py`.
- Quality scoring can run after validation and surface results in the UI or API.
- Existing case packages remain readable without migration.
- Future Codex contexts can understand the product direction from `docs/` alone.

