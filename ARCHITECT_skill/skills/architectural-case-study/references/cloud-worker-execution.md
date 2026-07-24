# Cloud Worker Execution Contract

Use this contract when the architectural-case-study workflow runs as an asynchronous cloud job. Keep `case.md` and `case.json` as the canonical research output; do not add worker fields to `case.json`.

## Contract Boundaries

- The API creates a job from `worker-templates/generation-request.json` and assigns an immutable `job_id`.
- The editor resolves ambiguity with `worker-templates/candidate-confirmation.json`; accept only a candidate ID previously written to that job's `disambiguation.json`.
- The worker writes only beneath its job workspace until validation and review complete.
- Store state, events, candidate choices, quality reports, and publication decisions outside the case package.
- Promote a completed package to the canonical case store only after validation passes and an administrator approves it.
- Never publish an image merely because it was downloaded for research. Public eligibility is a separate, explicit decision.

## Job Workspace

Use this layout in a mounted volume or private object storage:

```text
jobs/<job_id>/
  request.json
  events.jsonl
  artifacts/
    disambiguation.json
    package/<slug>/
      case.md
      case.json
      images/
      sources/
    validation.json
    quality-report.md
    publish-manifest.json
```

The final canonical package has the same inner structure as `artifacts/package/<slug>/`. Promotion must copy that package atomically; a failed or cancelled job must never overwrite an existing canonical slug.

## States And Gates

Use exactly these states for a generation job:

| State | Worker action | Exit condition |
| --- | --- | --- |
| `created` | Persist and validate request shape. | Start worker. |
| `disambiguating` | Search and identify project candidates. | One high-confidence identity, or candidates written. |
| `waiting_for_confirmation` | Stop all full-package writing. | Editor confirms a candidate. |
| `generating` | Collect sources, analyze, write draft package and research images. | Draft files exist. |
| `validating` | Run the bundled package validator. | Validator exits 0. |
| `scoring` | Run `check_case_package.py` and retain the report. | Score/grade captured. |
| `awaiting_review` | Create publication manifest; do not promote or deploy. | Admin approves/rejects. |
| `published` | Promote approved package and trigger site build. | Build receipt stored. |
| `failed` | Preserve diagnostics and partial private artifacts. | Terminal. |
| `cancelled` | Stop work without promotion. | Terminal. |

Treat a validator non-zero exit, a `BLOCKED` grade, or a score below 70 as a transition to `failed`, unless an administrator creates a new explicit exception/review action. Do not silently retry a content-quality failure.

## Worker Procedure

1. Read `request.json`, verify `mode` is `generate`, and emit a `started` event.
2. Read the required skill references: source quality, analysis taxonomy, Markdown template, JSON schema, and this contract. Read the local PDF workflow when the request includes PDFs.
3. Run the disambiguation gate. Write `disambiguation.json`; if a human decision is needed, emit the state change and exit cleanly.
4. After confirmation, gather sources according to the source-quality rules. Record every retained source, uncertainty, and access limitation in the draft package.
5. Create the draft only under `artifacts/package/<slug>/`; use the existing package template and schema without extra worker keys.
6. Treat downloaded images as private research assets. Populate their normal `image_metadata` and Markdown placement, but leave public selection to the publication manifest.
7. Run `validate_case_package.py` followed by `check_case_package.py --output .../quality-report.md`. Serialize the command result into `validation.json`.
8. On a passing score, create `publish-manifest.json`, set `awaiting_review`, and emit a terminal-for-worker event. The worker must not decide publication itself.

## Events, Retries, And Idempotency

- Append one JSON object per lifecycle event using `worker-templates/job-event.json`.
- Include the same `job_id`, attempt number, state, timestamp, and machine-readable event type in every event.
- Accept one request idempotency key. A second submission with the same key must return the original job instead of creating another package.
- Retry only transport, provider, download, or temporary storage failures. Resume from the last completed state and preserve prior artifacts.
- Do not retry `waiting_for_confirmation`, validation errors, source sufficiency decisions, or quality failures as if they were infrastructure errors.
- Never infer a slug from untrusted paths. Normalize it to lowercase ASCII hyphen-case, reject traversal, and reserve it before promotion.

## Security And Publication Rules

- Keep model credentials, search credentials, and object-store credentials in environment variables; never write them into requests, events, prompts, Markdown, or case JSON.
- Treat uploaded PDFs as untrusted files. Store them under the job workspace and expose only controlled paths to the worker.
- Record source URLs and normal image copyright notes in the package, but serve research assets privately until review.
- The public build may include only `approved_for_public: true` image entries from the publication manifest. For every other image, render its source link and a research/reference notice instead of a local file.
- Preserve failed and cancelled artifacts for debugging according to the deployment retention policy; do not publish them.

## Provider Adapter Boundary

The worker may use different model or web-search providers. Keep provider calls behind an adapter that accepts the request, current state, required references, and staged workspace paths, then returns structured candidates or generated artifacts. The adapter must not bypass the gates above or mutate canonical storage directly.

## Minimal Runtime Scope

`ARCHITECT_skill/worker_runtime/` implements only `created -> disambiguating -> waiting_for_confirmation` for local verification. Its business pipeline depends on an `LLMProvider` interface; the first real implementation is an OpenAI Responses API client configured entirely through environment variables. It validates every model result against `worker_runtime/schemas/disambiguation-result.schema.json` before writing `artifacts/disambiguation.json`.
