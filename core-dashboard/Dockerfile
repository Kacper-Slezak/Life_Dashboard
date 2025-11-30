FROM python:3.11-slim as builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir=/usr/src/app/wheels -r requirements.txt

FROM python:3.11-slim

WORKDIR /app

COPY --from=builder /usr/src/app/wheels /wheels

COPY . .

# SRE: Install only runtime libraries, not development packages
# SRE: Remove apt cache after installation
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 && \
    pip install --no-cache-dir --find-links=/wheels -r requirements.txt && \
    rm -rf /var/lib/apt/lists/*

# SRE: Run as a non-root user for improved security
RUN useradd -m -u 1001 appuser
USER appuser

# SRE: Fixed CMD path (main.py is in /app, not /app/app)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]