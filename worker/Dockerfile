# Worker image (FastAPI). Works on Fly.io and Render (Docker runtime).
FROM python:3.12-slim

WORKDIR /app

# Install deps first for layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code (config reads settings from the environment, not a .env file, in prod).
COPY app ./app
COPY scripts ./scripts

ENV PORT=8000
EXPOSE 8000

# Honour the platform-provided $PORT (Fly/Render set it).
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
