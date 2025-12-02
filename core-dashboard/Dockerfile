FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies (like gcc and libpq-dev for psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements.txt and build wheels
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir=/usr/src/app/wheels -r requirements.txt


# Stage 2: Final - Use a clean, minimal image
FROM python:3.11-slim

WORKDIR /app

# Copy built wheels from the builder stage
COPY --from=builder /usr/src/app/wheels /wheels

# Copy application code
COPY requirements.txt .

COPY . .

# Install runtime dependencies (like libpq5) and install Python packages from wheels
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 && \
    pip install --no-cache-dir --find-links=/wheels -r requirements.txt && \
    rm -rf /var/lib/apt/lists/*

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]