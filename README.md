# IONDU

PWA para PyMEs ecuatorianas: facturación electrónica, ventas, gastos, inventario, dashboard financiero y un agente de IA.

## Estructura

| Carpeta / archivo | Contenido |
|---|---|
| `frontend/` | Aplicación Angular (PWA) con su `Dockerfile` y configuración de Nginx. |
| `backend/` | API (FastAPI) y worker en Python, una sola imagen Docker. Expone `/api/health`. |
| `docs/` | Documentación del proyecto (ver abajo). |
| `docker-compose.yml` | Define los servicios; es el que usa el despliegue. |
| `docker-compose.override.yml` | Solo desarrollo local: publica `http://localhost:8080`. |
| `.env.example` | Plantilla de variables de entorno (sin secretos). |

## Ejecutar con Docker

```bash
cp .env.example .env
# Completar en .env: POSTGRES_PASSWORD, APP_ENV=development, las cuatro conexiones
# (DATABASE_URL, AUTH_DATABASE_URL, WORKER_DATABASE_URL, MIGRATION_DATABASE_URL;
# ver la nota en .env.example)
# DEV_USER_ID=11111111-1111-1111-1111-111111111111, STORAGE_ACCESS_KEY_ID y STORAGE_SECRET_ACCESS_KEY
# (cualquier valor: son del almacenamiento S3 local) y AUTH_JWT_PRIVATE_KEY, que se genera con:
#   docker compose run --rm --no-deps api python -m scripts.generar_llave_jwt
docker compose up --build
# abrir http://localhost:8080 (API interactiva en http://localhost:8080/api/docs)
```

Base local por primera vez (con Docker encendido y el `.env` completo). Todo corre dentro de los
contenedores; no hace falta Python instalado:

```powershell
docker compose up -d db storage
docker compose run --rm --no-deps api alembic upgrade head                      # esquema completo
docker compose run --rm --no-deps api python -m scripts.configurar_roles_locales # login de iondu_app, iondu_auth e iondu_worker
docker compose up -d --build
docker compose run --rm --no-deps -e DEMO_PASSWORD="<mínimo 10 caracteres>" api python -m scripts.cargar_datos_demo
```

La API se conecta como `iondu_app` (negocio) e `iondu_auth` (login y contraseñas) y el worker como
`iondu_worker`, igual que en producción: sin privilegios de administrador y con RLS. `AUTH_DATABASE_URL`
debe estar en `.env` antes de `alembic upgrade head` (Compose la exige para el servicio `api`). Si algo falla con "permission denied", falta un permiso en las migraciones
(ver `DECISIONES.md` 1.9).

Agente de IA en local (opcional): instalar [Ollama](https://ollama.com), descargar el modelo con
`ollama pull qwen2.5:7b` y poner en `.env` `LLM_BASE_URL=http://host.docker.internal:11434/v1`. Sin esa variable, el
agente responde que no está configurado y el resto del sistema funciona igual. Para que lea fotos de facturas:
`ollama pull qwen2.5vl:7b` y `LLM_VISION_MODEL=qwen2.5vl:7b` (unos 6 GB; con 8 GB de GPU, Ollama alterna los dos modelos).
Para los mensajes de voz: `COMPOSE_PROFILES=ia` y `STT_BASE_URL=http://stt:8000/v1` levantan un Whisper local en CPU
(la primera vez descarga unos 500 MB).

Facturación sin certificado `.p12` (demostración): con `SRI_SIMULADO_EMPRESAS=1` en `.env`, la empresa demo (en
ambiente de pruebas) emite facturas firmadas con un certificado de prueba que el worker "autoriza" sin enviarlas al
SRI. El RIDE dice "SIMULADO - SIN VALIDEZ TRIBUTARIA". En producción no tiene efecto (`DECISIONES.md` 2.33).

Inicio de sesión: `admin@demo.iondu.ec` (Administrador) u `operador@demo.iondu.ec` (Operativo), con la
contraseña de `DEMO_PASSWORD`. Para crear usuarios o cambiar contraseñas:

```powershell
docker compose exec api python -m scripts.crear_usuario --email ana@empresa.ec --nombre "Ana Torres" --rol Operativo
```

## Pruebas del backend

Corren con un usuario **restringido** (`iondu_test_runner`, sin SUPERUSER ni BYPASSRLS), igual que en
el CI, para demostrar que las políticas RLS aíslan a cada empresa. Crearlo una vez (con Docker encendido),
eligiendo una clave:

```powershell
docker exec proyectoiondu-db-1 psql -U iondu -d postgres -c "CREATE DATABASE iondu_test OWNER iondu" -c "CREATE ROLE iondu_test_runner LOGIN NOSUPERUSER NOBYPASSRLS PASSWORD '<clave>'"
docker exec proyectoiondu-db-1 psql -U iondu -d iondu_test -c "GRANT CONNECT, CREATE, TEMP ON DATABASE iondu_test TO iondu_test_runner" -c "GRANT USAGE, CREATE ON SCHEMA public TO iondu_test_runner"
```

Luego, desde `backend/`:

```powershell
$env:TEST_DATABASE_URL = "postgresql+psycopg://iondu_test_runner:<clave>@127.0.0.1:15432/iondu_test"
.venv\Scripts\python.exe -m pytest -q
```

Autenticación y RLS con las **migraciones reales** y los roles `iondu_app`, `iondu_auth` e
`iondu_worker` (`tests/postgres_auth/`). Como asignan contraseñas a roles globales, necesitan un
PostgreSQL **desechable** y se niegan a correr si encuentran otra base (como `iondu`):

```powershell
docker run -d --rm --name iondu-pg-auth -p 127.0.0.1:26432:5432 -e POSTGRES_USER=iondu -e POSTGRES_PASSWORD=pruebas -e POSTGRES_DB=postgres postgres:17-alpine
$env:TEST_ADMIN_DATABASE_URL = "postgresql+psycopg://iondu:pruebas@127.0.0.1:26432/postgres"
.venv\Scripts\python.exe -m pytest -q tests/postgres_auth
docker stop iondu-pg-auth
```

## Ejecutar sin Docker (desarrollo del frontend)

```bash
cd frontend
npm ci
npm start
```

## Documentación

- [`docs/ESTADO.md`](docs/ESTADO.md): qué está hecho, qué falta y los siguientes pasos (empieza aquí).
- [`docs/DECISIONES.md`](docs/DECISIONES.md): decisiones tomadas y por qué (Docker, VPS con Coolify, Supabase, diseño…).
- [`docs/REQUISITOS.md`](docs/REQUISITOS.md): requerimientos funcionales y no funcionales (corregidos).
- [`docs/PRESUPUESTO.md`](docs/PRESUPUESTO.md): presupuesto de infraestructura y servicios (corregido).
- [`docs/DESPLIEGUE.md`](docs/DESPLIEGUE.md): guía de despliegue para quien administra el servidor.
- [`docs/CORRECCIONES_PDF.md`](docs/CORRECCIONES_PDF.md): cambios pendientes en el PDF del proyecto.
- `docs/Proyecto Final Ing. Software I (2).pdf` y `docs/Tabla de presupuesto.xlsx`: documentos originales.

Los videos con las aprobaciones de requerimientos y del mockup/prototipo están disponibles en:

https://drive.google.com/drive/folders/1JLW7mLXDvMrNdCuupSsPG6LMujQiLPO-?usp=sharing
