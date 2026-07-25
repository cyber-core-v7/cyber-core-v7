FROM python:3.9-slim

# System deps for building some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ build-essential libffi-dev python3-dev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure data dirs exist
RUN mkdir -p /app/data /app/exports

ENV PORT=8000
EXPOSE 8000

CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "main:app", "--bind", "0.0.0.0:8000"]
