FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libffi8 \
    fonts-dejavu-core \
    fonts-liberation \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY backend ./backend
COPY frontend ./frontend

EXPOSE 8000

CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
