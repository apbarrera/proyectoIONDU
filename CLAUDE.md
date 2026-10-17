# Directivas de Proyecto (IONDU)

## Comportamiento y Respuestas
- Responde siempre en español.
- Ve directo al código y a la solución técnica sin introducciones ni despedidas innecesarias.

## Git y Control de Versiones
- NUNCA agregues `Co-authored-by: Claude` ni ninguna mención a IA en los commits.
- Commits exclusivamente a nombre del usuario local, usando formato conventional commits en español (ej: `feat: ...`, `fix: ...`).
- Nunca commitear `.env`, claves maestras, contraseñas ni certificados `.p12`.

### Formato de commits (obligatorio en cada commit)
Formato: `tipo(alcance): descripcion en minusculas, en español, imperativo, sin punto final` (máx. ~72 caracteres). El alcance es opcional.

- Tipos: `feat` (funcionalidad nueva), `fix` (corrección de error), `refactor` (reestructura sin cambiar comportamiento), `docs`, `chore` (mantenimiento, dependencias, variables), `ci` (GitHub Actions), `test`, `perf`, `style`.
- Alcances: `backend`, `frontend`, `db`, `auth`, `docker`, `nginx`, `sri`, `ia`, `worker`, `inventario`, `gastos`, `ventas`, `dashboard`.
- Un commit por cambio lógico; no mezclar renombres/movimientos con cambios de contenido.
- Antes de commitear, revisar `git status` para confirmar que no entra `.env`, `*.p12`, `*.pfx` ni `*.zip`.

Ejemplos:
```
feat(backend): crear API FastAPI con endpoint /api/health
feat(db): crear esquema multi-tenant con migraciones Alembic
feat(db): activar Row Level Security por id_empresa
feat(auth): integrar login de Angular con Supabase Auth
chore: agregar variables de Supabase y SRI a .env.example
ci: agregar workflow de GitHub Actions para lint, pruebas y build
fix(nginx): corregir cache del service worker
docs: actualizar requisitos del modulo de gastos
```

## Base de Datos y Backend (FastAPI + PostgreSQL)
- La base de datos es exclusivamente PostgreSQL (Supabase). Prohibido usar sintaxis o tipos de MySQL.
- Todo endpoint y consulta SQL/ORM debe aislar datos filtrando estrictamente por `id_empresa`.
- Conexión a Supabase siempre mediante Session Pooler (puerto 5432).
- Usar zona horaria `America/Guayaquil` para fechas y comprobantes del SRI.
- Los certificados `.p12` no se guardan como archivos en disco; se descifran solo en memoria RAM al momento de firmar.
- El backend debe exponer siempre el endpoint `/api/health`.

## Frontend (Angular)
- Todas las peticiones HTTP al backend deben usar la ruta relativa `/api/...` (sin URLs absolutas fijas).
- Al cerrar sesión, limpiar `localStorage` y la caché del service worker de la PWA.

## Reglas de Negocio
- La IA nunca puede crear ni alterar ingresos directamente; solo operan por facturación electrónica o venta manual.
- Toda acción sugerida por IA sobre inventario o gastos requiere confirmación explícita previa del usuario.
- El Dashboard financiero es de acceso exclusivo para rol `Administrador`.

## Docker y Despliegue (Coolify)
- Los contenedores deben ser sin estado (stateless): archivos, PDFs e imágenes van a Supabase Storage.
- En `docker-compose.yml`, usar `expose` para servicios internos (`api`, `worker`) y no publicar puertos innecesarios a internet.