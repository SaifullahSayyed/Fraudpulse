# Stage 1: Build environment
FROM python:3.11-slim as builder
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc python3-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Stage 2: Final minimal image
FROM python:3.11-slim
WORKDIR /app

COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache /wheels/*

COPY . .

# Default port for FastAPI
EXPOSE 8000
# Default port for Streamlit
EXPOSE 8501

# The startup command is handled in docker-compose
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
