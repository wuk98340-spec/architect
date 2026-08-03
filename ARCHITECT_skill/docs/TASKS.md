# Architectural Case Study Website Tasks

## Phase 0: Documentation Scaffold

- [x] Add product specification.
- [x] Add architecture notes.
- [x] Add implementation task list.
- [x] Add Codex handoff notes.
- [x] Keep existing Skill, scripts, case packages, and site output unchanged.

Acceptance:

- `docs/PRODUCT_SPEC.md`, `docs/ARCHITECTURE.md`, `docs/TASKS.md`, and `docs/CODEX_HANDOFF.md` exist.
- The docs state that `case.md` and `case.json` formats remain unchanged.
- The docs state that `case-packages/` must not be added to Git.

## Phase 1: Backend Scaffold

- Create a backend app directory without moving existing scripts.
- Add a minimal Python/FastAPI server.
- Add repository path configuration for `case-packages/`, `quality-reports/`, Skill scripts, and generated `site/`.
- Implement read-only case listing from existing `case-packages/*/case.json` and `case.md`.
- Implement case detail loading with validation status.
- Implement local image serving for `images/`.

Acceptance:

- Backend can list existing cases.
- Backend can return one case's markdown, structured JSON, source summary, image metadata, and validation state.
- Backend does not modify case package files during read-only operations.

## Cloud Worker Foundation

- [x] Define the generation-job workspace, state machine, failure gates, and canonical-promotion rule.
- [x] Add JSON templates for request, candidate confirmation, disambiguation, events, validation, and publication review.
- [x] Add the provider-neutral worker prompt template and reference it from the case-study skill.
- [x] Implement a local, provider-neutral AI runtime for disambiguation, editor confirmation, bounded web retrieval, private draft creation, and existing package validation.
- [x] Add OpenAI Responses and DeepSeek Chat Completions provider adapters with structured-output validation; neither adapter can write canonical packages.
- [ ] Implement the FastAPI job API and persistence layer against these templates.
- [ ] Implement the production job API, persistence layer, retries, and quality-scoring runner; it must not write directly to canonical packages.

## Phase 2: Frontend Scaffold

- Create a frontend app directory.
- Build case library list with search/filter.
- Build case detail page rendering `case.md` and local images.
- Add panels for facts, source quality, uncertainty, incomplete reason, and image metadata.
- Add clear empty/error states for invalid or incomplete historical packages.

Acceptance:

- User can browse existing packages through the frontend.
- Images referenced by `case.md` render through backend-served URLs.
- Invalid JSON or validation failures are visible instead of silently hidden.

## Phase 3: Generation Orchestration MVP

- Add generation request model in the backend.
- Add job status states: `created`, `disambiguating`, `waiting_for_confirmation`, `generating`, `validating`, `scoring`, `completed`, `failed`.
- Implement query submission endpoint.
- Implement disambiguation candidate storage and confirmation endpoint.
- Connect confirmed jobs to the existing Skill/Agent generation workflow.
- Run `validate_case_package.py` after package generation.
- Run `check_case_package.py` or `review_case_quality.py` after validation.

Acceptance:

- User can submit a query and receive candidates when ambiguous.
- User confirmation is required before full generation for ambiguous targets.
- Completed jobs produce the original package files under `case-packages/<slug>/`.
- Validation and quality results are attached to the job result.

## Phase 4: Repair And Review Workflow

- Add UI for selecting an existing case and repair target.
- Backend should call the repair workflow only after identifying package and scope.
- Preserve backup behavior through `backup_case_package.py`.
- Show validation and score changes after repair.

Acceptance:

- Scoped repairs do not rewrite unrelated package sections.
- `case.md` and `case.json` remain synchronized.
- A repair creates a revision backup before mutation.

## Phase 5: Static Site Integration

- Keep `scripts/build_site.py` available as an export/build command.
- Add backend or UI trigger for rebuilding `site/` only after validation passes.
- Document that direct edits to `site/` are not durable.

Acceptance:

- Static site rebuild remains optional and derived.
- Rebuilding does not mask validation failures.

## Implementation Guardrails

- Do not redesign `case.json`.
- Do not add generated case packages to Git.
- Do not commit local images unless a future policy explicitly changes this.
- Do not overwrite user or generated work outside the requested scope.
- Use existing validation before presenting generated packages as complete.
