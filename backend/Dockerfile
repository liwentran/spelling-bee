# Built by CI from the repo root: docker build -f backend/Dockerfile .
FROM python:3.12-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
# main.py serves /frontend at /static.
COPY frontend/ /frontend

# Single worker: GameState lives in process memory.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
