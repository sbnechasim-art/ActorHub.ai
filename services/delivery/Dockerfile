FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

COPY src/ src/

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8004/health || exit 1

EXPOSE 8004

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8004"]
