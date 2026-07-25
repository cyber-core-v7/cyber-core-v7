# CYBER-CORE v7.0

Quick setup and run instructions (local & container).

## Prerequisites
- Python 3.9.x installed (match runtime.txt)
- git
- (Optional) Docker

## Local development (recommended)
1. Clone:
   git clone https://github.com/cyber-core-v7/cyber-core-v7.git
   cd cyber-core-v7

2. Create virtualenv and install:
   python3.9 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt

3. Prepare environment & directories:
   cp .env.example .env
   # Edit .env and set SECRET_KEY
   mkdir -p data exports

4. Initialize DB (the app creates/seed DB automatically on first run).

5. Run in development:
   uvicorn main:app --reload --host 0.0.0.0 --port ${PORT:-8000}

6. For production:
   # Procfile uses gunicorn + uvicorn worker
   # Or run via Docker (see Dockerfile)

## Docker (optional)
Build and run:
   docker build -t cyber-core-v7 .
   docker run -p 8000:8000 -e PORT=8000 -v $(pwd)/data:/app/data cyber-core-v7

## Troubleshooting
- If build fails on native extensions, ensure system packages listed in packages.txt are installed.
- Ensure `data/` is writable by the process.
- Check logs for stack traces and post them if you need deeper debugging.
