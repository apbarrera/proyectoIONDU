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
docker compose up --build
# abrir http://localhost:8080
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
