FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    ARCHITECT_API_HOST=0.0.0.0

WORKDIR /app

COPY ARCHITECT_skill/worker_runtime/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY . .

EXPOSE 8080

CMD ["sh", "-c", "cd /app/ARCHITECT_skill && python -m backend_api.render_start"]
