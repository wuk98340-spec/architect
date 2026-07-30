FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    ARCHITECT_API_HOST=0.0.0.0 \
    ARCHITECT_DATA_ROOT=/tmp/architect

WORKDIR /app

COPY ARCHITECT_skill/worker_runtime/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy only runtime inputs. The workspace also contains browser caches, local
# diagnostics, recovery archives, and generated design artifacts; copying the
# whole tree makes the Cloud Run image too large to publish.
COPY ARCHITECT_skill/backend_api /app/ARCHITECT_skill/backend_api
COPY ARCHITECT_skill/worker_runtime /app/ARCHITECT_skill/worker_runtime
COPY ARCHITECT_skill/skills /app/ARCHITECT_skill/skills
COPY case-packages /app/case-packages
COPY architecture-case-site/public /app/architecture-case-site/public

EXPOSE 8080

CMD ["sh", "-c", "cd /app/ARCHITECT_skill && if [ \"$ARCHITECT_SERVICE_ROLE\" = worker ]; then python -m backend_api.research_worker; else python -m backend_api.render_start; fi"]
