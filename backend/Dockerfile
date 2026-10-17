# syntax=docker/dockerfile:1.7
# ============================================================
# IONDU · Backend Python (API FastAPI) + Worker
# UNA sola imagen, dos procesos: la API y el worker se diferencian
# solo por el "command" en docker-compose.yml.
# Targets: runtime (por defecto) y test (ejecuta pytest al construir).
# ============================================================
ARG PYTHON_VERSION=3.12

# ---------- Etapa 1: dependencias ----------
# Cuando se agregue la firma XAdES-BES del SRI (python-xmlsec), instalar aquí
# build-essential, pkg-config, libxml2-dev y libxmlsec1-dev, y las librerías
# de ejecución (libxml2, libxmlsec1-openssl) en la etapa runtime.
FROM python:${PYTHON_VERSION}-slim-bookworm AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt

# ---------- Etapa de pruebas: docker build --target test . ----------
FROM builder AS test
COPY requirements-dev.txt .
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements-dev.txt
WORKDIR /src
COPY app ./app
COPY tests ./tests
RUN python -m pytest -q

# ---------- Etapa 2: runtime ----------
FROM python:${PYTHON_VERSION}-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    TZ=America/Guayaquil

# tini = PID 1 que reenvía señales (apagado limpio en redeploys).
RUN apt-get update && apt-get install -y --no-install-recommends tzdata tini \
    && rm -rf /var/lib/apt/lists/*

# Usuario sin privilegios
RUN groupadd --system --gid 10001 app \
 && useradd --system --uid 10001 --gid app --home-dir /app --shell /usr/sbin/nologin app

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --chown=app:app app ./app

USER app
EXPOSE 8000

ENTRYPOINT ["/usr/bin/tini", "--"]

# Por defecto arranca la API. El worker sobreescribe "command" en el compose.
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "2", \
     "--proxy-headers", "--forwarded-allow-ips", "*", \
     "--timeout-graceful-shutdown", "30"]
