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

# SRE: Instaluj tylko bibliotekę wykonawczą, nie deweloperską
# SRE: Usuń cache apt po instalacji
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 && \
    pip install --no-cache-dir --find-links=/wheels -r requirements.txt && \
    rm -rf /var/lib/apt/lists/*

# SRE: Uruchom jako użytkownik non-root dla bezpieczeństwa
RUN useradd -m -u 1001 appuser
USER appuser

# SRE: Poprawiona ścieżka CMD (main.py jest w /app, nie /app/app)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]