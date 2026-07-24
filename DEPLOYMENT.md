# Render deployment

`render.yaml` deploys one paid Render Web Service with a persistent disk. The
single process serves both the generated site and its API, so browser requests
use the same origin:

- `GET /` and other files are served from `architecture-case-site/public/`.
- `GET /healthz` is the Render health check.
- `POST /api/jobs`, `GET /api/jobs/{job_id}`, `POST /api/jobs/{job_id}/confirm`,
  `GET /api/jobs/{job_id}/result`, and `POST /api/jobs/{job_id}/save` are the
  API entry points.

At boot, `ARCHITECT_skill.backend_api.render_start` seeds an empty
`/var/data/case-packages` directory from the repository, rebuilds `public/`
from that durable library, and starts `python -m backend_api`. A successful
save copies a validated package to the same durable library and rebuilds the
served site. Jobs are persisted under `/var/data/worker-jobs`.

Set `DEEPSEEK_API_KEY` in Render's Blueprint prompt or service environment;
do not add it to the repository. To switch providers, change
`ARCHITECT_LLM_PROVIDER` and supply the matching `OPENAI_API_KEY` or
`DEEPSEEK_API_KEY`. The other worker settings in `render.yaml` have the same
meaning as `ARCHITECT_skill/worker_runtime/.env.example`.

The current worker is intentionally started in the API request that confirms a
candidate; it is not an independent Render background worker. This preserves
the present job state machine, but a very long generation occupies one API
request thread. Moving it to a queue-backed Render Worker is a later
architecture change, not a deployment-config toggle.
