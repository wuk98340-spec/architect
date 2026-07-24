# Minimal AI Worker Runtime

This runtime implements a private, minimum viable research flow:

```text
generation request -> validated disambiguation -> editor confirmation
-> controlled web retrieval -> provider draft -> package validation -> awaiting review
```

Run from `ARCHITECT_skill` after exporting environment variables. The recommended
production configuration is DeepSeek:

```powershell
$env:DEEPSEEK_API_KEY = "..."
$env:ARCHITECT_LLM_PROVIDER = "deepseek"
$env:ARCHITECT_LLM_MODEL = "deepseek-v4-flash"
python -m worker_runtime --query "Villa Savoye, Le Corbusier, Poissy" --output-root .\tmp\worker-jobs
```

The first command stops after writing `artifacts/disambiguation.json`, including
one or more candidate IDs. Confirm one emitted candidate to start private
research and draft creation:

```powershell
python -m worker_runtime --confirm-job <job_id> --candidate-id <candidate_id> --output-root .\tmp\worker-jobs
```

To re-run validation for a private draft after a worker-code fix, without making
another model request:

```powershell
python -m worker_runtime --validate-job <job_id> --output-root .\tmp\worker-jobs
```

The confirmation command writes only under
`tmp/worker-jobs/<job_id>/artifacts/package/<slug>/`. It retrieves a bounded
set of web pages, collects a bounded set of source-page image candidates when
available, writes `research-results.json`, asks the configured provider to
generate a source-bounded full-research `case.json` and `case.md`, then runs
both package validation and the repository quality scorer. The reports are
written as `validation.json` and `quality-report.json`. A generated draft stays
private until the user opens its preview and explicitly saves it; it is never
copied to `case-packages/` automatically.

For an offline contract check that does not call an LLM:

```powershell
python -m worker_runtime --query "Villa Savoye, Le Corbusier, Poissy" --provider fixture --output-root .\tmp\worker-jobs
```

The command prints the generated `artifacts/disambiguation.json` path. It also writes `request.json` and append-only `events.jsonl` under `tmp/worker-jobs/<job_id>/`.

Environment variables:

- `OPENAI_API_KEY`: required only for `openai`; never read from source files.
- `DEEPSEEK_API_KEY`: required only for `deepseek`; never read from source files.
- `ARCHITECT_LLM_PROVIDER`: `openai` (default), `deepseek`, or `fixture` for offline testing.
- `ARCHITECT_LLM_MODEL`: model ID. Its DeepSeek default is `deepseek-v4-flash`; its OpenAI default is `gpt-5.6`.
- `OPENAI_BASE_URL`: optional compatible API base URL, default OpenAI's `/v1` base.
- `DEEPSEEK_BASE_URL`: optional DeepSeek-compatible API base URL, default `https://api.deepseek.com`.
- `ARCHITECT_LLM_TIMEOUT_SECONDS`: request timeout, default `90`.
- `ARCHITECT_LLM_MAX_TOKENS`: DeepSeek maximum output tokens, default `16000`.

The DeepSeek adapter calls its OpenAI-compatible Chat Completions API with JSON
mode. It then validates the returned object locally against
`schemas/disambiguation-result.schema.json`; a syntactically valid but
schema-invalid response is never written as an artifact.

The retrieval stage uses server-rendered web-search results without a separate
search credential, with Bing and DuckDuckGo fallbacks. It passes search result
metadata and a bounded plain-text page excerpt to the model. Every
`case.json.sources[].url` must be one of those retrieved URLs, which prevents
the model from adding uncaptured citations.

## Minimal Backend API

The API is a thin HTTP wrapper around this runtime: it does not duplicate the
research, generation, validation, or worker state-transition logic. It uses the
same private `tmp/worker-jobs` storage and leaves the CLI available.

A generated private draft is not added to the library automatically. The user
opens the preview page, reads the complete case, and explicitly saves it. Only
then does the API copy the already-validated package into `case-packages/` and
rebuild the static case-library index.

```powershell
python -m backend_api
```

The server listens on `http://127.0.0.1:8000` by default. Set
`ARCHITECT_JOBS_ROOT` or `ARCHITECT_API_PORT` to override the job directory or
port. The worker provider is configured with the same environment variables as
the CLI.

```powershell
# Create a job; response contains status=awaiting_confirmation and candidates.
Invoke-RestMethod http://127.0.0.1:8000/api/jobs -Method Post -ContentType application/json -Body '{"query":"Captain''s House"}'

# Inspect a job.
Invoke-RestMethod http://127.0.0.1:8000/api/jobs/<job_id>

# Confirm an emitted candidate. This runs the existing worker confirmation flow.
Invoke-RestMethod http://127.0.0.1:8000/api/jobs/<job_id>/confirm -Method Post -ContentType application/json -Body '{"candidate_id":"<candidate_id>"}'

# Read the private draft and validator report once available.
Invoke-RestMethod http://127.0.0.1:8000/api/jobs/<job_id>/result

# Save a validated, user-approved preview to the formal case library.
Invoke-RestMethod http://127.0.0.1:8000/api/jobs/<job_id>/save -Method Post -ContentType application/json -Body '{}'
```
