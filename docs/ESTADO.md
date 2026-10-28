# IONDU · Estado del proyecto y siguientes pasos

> Resumen de traspaso. Última actualización: 25 de octubre de 2026 (primer módulo del backend: categorías y productos, con contrato en `API.md`).
> Documentos relacionados: [`DECISIONES.md`](DECISIONES.md) (el porqué de cada decisión) · [`REQUISITOS.md`](REQUISITOS.md) · [`PRESUPUESTO.md`](PRESUPUESTO.md) · [`DESPLIEGUE.md`](DESPLIEGUE.md) · [`CORRECCIONES_PDF.md`](CORRECCIONES_PDF.md)

## 1. Qué está hecho

### Infraestructura y repositorio
- Monorepo ordenado: `frontend/`, `backend/` y `docs/`.
- Docker con tres servicios: `web` (Angular + Nginx), `api` (FastAPI) y `worker`. `docker-compose.yml` es compatible con Coolify: solo `web` es público; `api` y `worker` usan `expose`.
- **PostgreSQL local para desarrollo** (servicio `db` en `docker-compose.override.yml`, que Coolify no lee): PostgreSQL 17 como Supabase, en `localhost:15432`. Exige `POSTGRES_PASSWORD` en el `.env` de cada uno.
- `.env.example` sin secretos. El `.gitignore` excluye `.env`, `*.p12`, `*.pfx`, `*.zip` y los archivos de Python (`.venv/`, `__pycache__/`, cachés).
- CI en GitHub Actions: pruebas del frontend, revisión con Ruff y pruebas del backend (dentro de Docker) y construcción de las imágenes **solo con `docker-compose.yml`** (lo mismo que usa Coolify).
- Corregido: `api` y `worker` compartían nombre de imagen y la construcción fallaba a veces con `image ... already exists`.
- `CLAUDE.md` con las reglas del proyecto y el formato obligatorio de commits.

### Backend: sesión con Supabase Auth (verificación del token)
- `app/core/seguridad.py`: verifica el JWT de Supabase (firma con sus llaves públicas, algoritmo, vencimiento,
  proyecto y audiencia) y bloquea los ataques `alg: none` y confusión con `HS256` (`DECISIONES.md` 2.3).
- **Empresa y rol desde el token** (`app/api/deps.py`): se buscan en `usuario_empresa`; el token manda sobre
  `X-Empresa-Id`, que solo vale sin token y en desarrollo. Permiso `SoloAdministrador` para lo exclusivo del
  Administrador (`DECISIONES.md` 2.14).
- `GET /api/me` devuelve el perfil con los mismos campos que `User` del frontend ([`API.md`](API.md), sección 5).
  Probado con llaves generadas en las pruebas; con Supabase real solo hace falta `SUPABASE_URL`.
- Modelos `Rol` y `UsuarioEmpresa` listos según el diseño acordado. **Falta la tabla `usuario_empresa` en la base**
  (esquema de Ariana); hasta entonces el login con token no se puede usar contra la base real.

### Backend: primer módulo (categorías y productos)
- Endpoints según [`API.md`](API.md): `GET/POST /api/product-categories` y `GET/POST /api/products`, `GET/PATCH /api/products/{id}`, con páginas, búsqueda y filtros (`categoryId`, `type`, `lowStock`).
- Capas: `models/` (empresa, categoría y producto, idénticos a `schema.sql`, comprobado con `alembic check`) → `repositories/` (cada repositorio recibe la empresa y todas sus consultas la filtran) → `services/` (reglas: categoría de la misma empresa, código único por empresa, el stock no se edita) → `schemas/` (validación y nombres del contrato) → `api/`.
- **Errores con formato único** (`app/core/errors.py`): `{"error": {"code", "message", "details"}}`, con mensajes de validación en español por campo.
- **Empresa provisional** (`app/api/deps.py`): solo con `APP_ENV=development` se toma del encabezado `X-Empresa-Id`; en cualquier otro entorno responde 401. Con Supabase Auth solo cambia esa función.
- Pendiente de la base: desactivar productos (falta la columna `activo`) y la restricción `UNIQUE` del código (hoy lo valida el servicio).
- Pruebas del módulo incluido el aislamiento entre empresas (137 en total en el backend). Las de base de datos usan `TEST_DATABASE_URL` (ver sección 3) y en el CI corren contra un PostgreSQL temporal.

### Backend: base de la facturación del SRI (adelanto del Sprint 2)
- `app/sri/identificacion.py`: valida cédula, RUC (persona natural, sociedad y entidad pública), pasaporte,
  consumidor final e identificación del exterior, con mensajes en español (criterio en `DECISIONES.md` 2.16).
- `app/sri/clave_acceso.py`: genera y valida la clave de acceso de 49 dígitos (`DECISIONES.md` 2.17).
- `app/sri/totales.py`: totales e IVA por tarifa con redondeo comercial (`DECISIONES.md` 2.18).
- `app/sri/factura_xml.py`: XML de la factura (versión 2.1.0) validado siempre contra el esquema oficial del SRI
  (`app/sri/xsd/`), sin firmar (`DECISIONES.md` 2.19).
- `app/sri/ride.py`: RIDE en PDF con el código de barras de la clave de acceso, generado a partir del XML (`DECISIONES.md` 2.20).
- `app/sri/servicios_web.py`: cliente de recepción y autorización del SRI, probado con respuestas simuladas (`DECISIONES.md` 2.21).
- `app/sri/emision.py` y `app/sri/firma.py`: flujo de emisión completo con la firma como pieza intercambiable (`DECISIONES.md` 2.22).
- Sin base de datos; 87 pruebas (ninguna se conecta al SRI).
- Falta para facturar: firma XAdES-BES y la prueba real contra el SRI de pruebas (ambas requieren el `.p12`); guardar ventas y facturas en la base y los reintentos en el worker (requieren el esquema corregido).

### Backend (base)
- FastAPI con `/api/health`, hora en `America/Guayaquil`, configuración solo por variables de entorno y documentación `/api/docs` únicamente fuera de producción.
- **Conexión a PostgreSQL** con SQLAlchemy 2.1 + psycopg 3 (`app/db/session.py`): una conexión compartida con pool pequeño, zona horaria de Ecuador y *timeout* de 5 s. Los endpoints piden la sesión con `Depends(get_db)`.
- `/api/health` informa también el estado de la base: `"database": "ok" | "error" | "not_configured"` (siempre responde 200 si el proceso vive).
- **Migraciones con Alembic** (`backend/alembic/`): configurado y probado, **todavía sin migraciones**. La primera será el esquema de `database/schema.sql` cuando tenga sus correcciones.
- **Clase base de los modelos** (`app/db/base.py`) con nombres de restricciones fijos; los modelos irán en `app/models/`.
- **Ruff** revisa y formatea el código (`backend/pyproject.toml`); las migraciones nuevas se formatean solas.
- Estructura por capas acordada (patrón Repositorio del PDF): `api/` (endpoints) → `schemas/` (datos de entrada y salida) → `services/` (reglas de negocio) → `repositories/` (consultas, siempre por `id_empresa`) → `models/` (tablas). Las carpetas se crean cuando se necesitan.
- Worker con latido (`/tmp/worker-heartbeat`) y apagado limpio ante SIGTERM.
- **Todavía sin login**: el frontend sigue con datos de ejemplo hasta conectar sus servicios a `/api/...`.

### Base de datos
- `database/schema.sql`: esquema inicial con 17 tablas (exportado con `pg_dump` desde PostgreSQL 18). Se probó cargarlo en PostgreSQL 17 sin errores.
- Pendiente de corregir según [`CORRECCIONES_PDF.md`](CORRECCIONES_PDF.md) y la sección 2.F de este documento.

### Frontend (rediseño completo de la base)
- **Colores:** morado como único acento, sobre blanco y negro, en tema claro y oscuro. Por defecto sigue al sistema, con botón de tema en la cabecera.
- **Tipografía:** Geist, incluida en la app (no se descarga de Google).
- **Íconos:** Phosphor. Se reemplazaron los 89 emojis. Se generan con `npm run icons`.
- **Logo:** vectorizado a SVG; cambia solo entre tema claro y oscuro. Se hizo a partir de un PNG, así que si el diseño entrega el SVG original conviene sustituirlo (`shared/components/logo/logo-mark.const.ts`).
- **Menú lateral:** retráctil a columna de íconos, redimensionable (arrastrando el borde o con el teclado), con varias secciones abiertas a la vez, recordando su estado. Cada sección muestra primero la pantalla a la que redirige.
- **Dashboard:** rejilla alineada, tarjetas de igual altura, gráfico de ingresos con ejes y datos de ejemplo relativos a la fecha actual.
- **Transición entre páginas:** la anterior desaparece al instante y la nueva se desvanece sobre un lienzo vacío.
- **Ventas y facturación unidas:** un solo módulo. Cada venta nueva lleva el interruptor "Emitir factura electrónica" **activado por defecto**; el historial muestra el estado de la factura (Autorizada, En proceso, Rechazada o Sin factura) con filtros, y el detalle permite emitir o reintentar (corrigiendo la cédula o el RUC). Las rutas antiguas `/billing/*` redirigen a Ventas.
- **Accesibilidad:** auditadas con Lighthouse 19 pantallas en escritorio, en tema claro y oscuro, y las principales en móvil: **100 en todas**. Incluye etiquetas vinculadas a sus campos, contraste, orden de encabezados, modales con foco atrapado y filas de tabla operables con teclado.
- **Móvil:** probado a 320, 390 y 768 px sin desborde horizontal. Las tablas se ven como tarjetas, y el menú lateral es un cajón que, cerrado, no recibe foco y se cierra con Escape.
- **Cierre de sesión:** limpia `localStorage`, `sessionStorage` y la caché del service worker (regla de `CLAUDE.md`).
- 72 pruebas del frontend.

### Documentación
- Requerimientos y presupuesto corregidos en Markdown (el presupuesto baja de $96,93 a $60,93 al mes).
- Guía de despliegue para quien administra el servidor.
- Lista exacta de cambios pendientes en el PDF original.

## 2. Qué falta, por orden

### Progreso del backend (estimado, 25/10/2026)

| Módulo (requisitos) | Avance | Hecho | Falta |
|---|---|---|---|
| Infraestructura | 90 % | Docker, base local, migraciones, CI, errores, Ruff | Desplegar en el VPS |
| 1. Usuarios, roles y empresa | 40 % | Verificación del token, empresa y rol desde `usuario_empresa`, permiso de Administrador, `/api/me` | Tabla `usuario_empresa` en la base, configuración de la empresa, gestión de usuarios |
| 2. Facturación y ventas | 50 % | Identificación, clave de acceso, totales e IVA, XML validado, RIDE, cliente del SRI, flujo de emisión | Firma y prueba real (`.p12`); clientes, ventas y reintentos (esquema) |
| 3. Gastos | 0 % | — | Gastos, proveedores, correo (IMAP) |
| 4. Productos e inventario | 55 % | Categorías y productos | Desactivar, movimientos, ajustes, alertas |
| 5. Dashboard | 0 % | — | Indicadores (necesita ventas y gastos) |
| 6. Agente IA | 0 % | — | Todo (Sprint 4) |
| 7. Recomendaciones | 0 % | — | Todo (Sprint 5) |

### Qué necesita el backend de cada uno

| # | Quién | Qué | Desbloquea en el backend | Urgencia |
|---|---|---|---|---|
| 1 | Ariana | Corregir el esquema (2.F). Para `usuario_empresa` y `rol` puede seguir `backend/app/models/usuario_empresa.py` y `rol.py`, ya escritos según lo acordado | Primera migración real; login con la base real; ventas, gastos y movimientos (dependen de `usuario`) | Alta |
| 2 | Equipo | Crear el proyecto de Supabase y pasar URL y claves por un canal seguro | Login real: validar el token y tomar la empresa del usuario | Alta |
| 3 | Equipo | Decidir el tipo de producto y si Recetas/Producción entran en el MVP | Cerrar productos; tablas de recetas si entran | Media |
| 4 | Denisse | Conectar `ProductsService` a `/api/products` (`API.md`, sección 6) | Primera pantalla con datos reales | Media |
| 5 | Denisse | Consumidor final con 13 nueves (2.F) | Evitar facturas rechazadas | Baja |
| 6 | Denisse | Login de Angular con Supabase Auth | Enviar el token al backend | Después del #2 |
| 7 | Cliente | Certificado `.p12`, RUC del emisor, VPS y dominio | Firmar y probar en el SRI de pruebas; desplegar | Pedirlo ya |

La facturación ya no puede avanzar mucho más sin el `.p12` del cliente y el esquema corregido de Ariana.

### A. Cosas rápidas
1. Confirmar que el CI de GitHub (pestaña **Actions**) esté en verde tras el último push.
2. Correr `/impeccable init` una vez en Claude Code, y decidir si se mantiene el hook que revisa la interfaz al editar.
3. Reemplazar el logo vectorizado cuando exista el SVG original.

### B. Frontend (lo que queda)
1. Revisión visual, pantalla por pantalla y en móvil, de Gastos, Inventario, Agente IA y Configuración. Se comprobó que no se desbordan y que cumplen accesibilidad, pero falta revisar su aspecto con ojo de diseño.
2. Pulido con `impeccable` (`/impeccable init` y luego `audit` y `polish`).
3. Probar la instalación de la PWA y el service worker en Chrome.
4. Cuando exista el backend: reemplazar los datos *mock* y la emisión simulada de facturas (`BillingAdapterService`) por llamadas reales a `/api/...`.
5. Validaciones de negocio de la factura (por ejemplo, límites del SRI para consumidor final) se harán en el backend en el Sprint 2.
### C. Sprint 1: lo que bloquea el resto
1. Crear el proyecto en **Supabase** (plan gratis para desarrollo). Pasar `SUPABASE_URL` y la dirección del *Session Pooler* (puerto 5432). **Las contraseñas y las claves no se pegan en el chat ni van al repositorio.**
2. Esquema multi-tenant con migraciones Alembic (`empresa`, `usuario_empresa`, `rol`, …) y RLS por `id_empresa`. Alembic ya está configurado: falta convertir el esquema corregido de `database/schema.sql` en la primera migración (ver 2.F).
3. Validar el JWT de Supabase en el backend y filtrar todo por `id_empresa`.
4. Conectar el login de Angular a Supabase Auth y reemplazar los datos *mock* por llamadas a `/api/...` (hoy todo el frontend usa datos de ejemplo).
5. Primer despliegue de `staging` en el VPS del cliente.

### D. Sprints siguientes
| Sprint | Contenido |
|---|---|
| 2 | Facturación con el SRI: generación del XML, firma XAdES-BES, autorización, ventas. **Requiere el certificado `.p12` del cliente.** |
| 3 | Gastos, inventario y lectura de facturas por correo (IMAP) con el worker. |
| 4 | Agente de IA (texto, imagen y voz) con confirmación humana obligatoria. |
| 5 | Dashboard con datos reales y recomendaciones. |
| 6 | Producción: pruebas de carga (100 usuarios), respaldos y entrega. |

### E. Fuera del código
- Aplicar [`CORRECCIONES_PDF.md`](CORRECCIONES_PDF.md) en el PDF del proyecto (MySQL a PostgreSQL, autenticación, firma electrónica, diagrama de despliegue).
- Pedir al cliente: certificado `.p12`, VPS (mínimo 2 vCPU y 4 GB de RAM) y dominio.

### F. Coordinación entre base de datos, backend y frontend
**Esquema (`database/schema.sql`), cambios pendientes** (detalle en [`CORRECCIONES_PDF.md`](CORRECCIONES_PDF.md)):
1. Tabla `usuario` con `contrasena_hash` e ID entero → `usuario_empresa` con el UUID de Supabase Auth (decisión 2.3).
2. Sin Row Level Security por `id_empresa` (decisión 2.4).
3. `empresa.firma_electronica VARCHAR(255)` → `.p12` y su clave cifrados (`BYTEA`) y `p12_fecha_vencimiento` (decisión 2.5).
4. Fechas `timestamp without time zone` → `timestamptz`.
5. `producto`: falta `activo` (RF-4.1 pide desactivar), `UNIQUE (id_empresa, codigo_principal)`, `CHECK` contra precios y stock negativos e índices por `id_empresa`.
6. `gasto`: falta `message_id_correo` y `clave_acceso` con `UNIQUE` por empresa (idempotencia del correo, RF-3.2).

Después de corregirlo, el esquema pasa a ser **la primera migración de Alembic**, y desde ahí todo cambio de la base es una migración nueva (no se vuelve a exportar `schema.sql`).

**Frontend vs. base de datos: el modelo de producto no coincide**

| Frontend (`Product`) | Base de datos (`producto`) | Requisitos |
|---|---|---|
| `sku` | `codigo_principal` | "código interno" |
| `type`: `simple`, `insumo`, `compuesto` | `tipo`: `VENTA` por defecto | venta, insumo o ambos (RF-4.1) |
| `active` | no existe | desactivar productos (RF-4.1) |
| no existe | `aplica_iva` | necesario para facturar |
| pantallas de Recetas y Producción | sin tablas | no aparecen en `REQUISITOS.md` |

**Frontend: consumidor final.** `new-sale.ts` y `sales-history.ts` usan `FINAL_CONSUMER_ID = '9999999999'`
(10 nueves); el SRI exige `9999999999999` (13 nueves) con el tipo de identificación `07`. Con 10, la factura sería
rechazada.

**Por decidir en equipo:** los valores del tipo de producto, y si Recetas y Producción entran en el MVP (si entran, hay que agregarlas a los requisitos y crear sus tablas).

**Contrato de la API:** en [`API.md`](API.md), empezando por productos (ya implementados en el backend). El JSON usará los nombres que ya usa el frontend (`sku`, `name`, `salePrice`…) y el backend los traduce a las columnas de la base. Así, en el frontend basta con cambiar `simulateRequest(...)` por llamadas reales en cada servicio.

## 3. Cómo trabajar en el proyecto

| Tarea | Comando |
|---|---|
| Levantar todo con Docker | `docker compose up -d --build` y abrir http://localhost:8080 |
| Desarrollar el frontend | `cd frontend && npm start` (http://localhost:4200) |
| Pruebas del frontend | `cd frontend && npx ng test --no-watch` |
| Pruebas del backend | `docker build --target test backend` (no hace falta Python local), o `cd backend && .venv\Scripts\python -m pytest` con el entorno virtual |
| Revisar y formatear el backend (Ruff) | `cd backend && .venv\Scripts\ruff check --fix . && .venv\Scripts\ruff format .` (el CI falla si no pasa) |
| Aplicar las migraciones de la base | `docker compose exec api alembic upgrade head` |
| Ver en qué migración está la base | `docker compose exec api alembic current` |
| Crear una migración nueva | `cd backend && alembic revision -m "descripcion"` y completar `upgrade()` y `downgrade()` en `backend/alembic/versions/`; luego `docker compose up -d --build api` y aplicarla |
| Base de datos local | PostgreSQL en `127.0.0.1:15432`, usuario y base `iondu`, contraseña `POSTGRES_PASSWORD` del `.env` |
| Probar la API a mano | Con `APP_ENV=development` en el `.env`: abrir http://localhost:8080/api/docs y enviar el encabezado `X-Empresa-Id` (la empresa debe existir en la tabla `empresa`) |
| Pruebas del backend con base de datos | Una vez: `docker compose exec db createdb -U iondu iondu_test`. Luego, desde `backend/`, definir `TEST_DATABASE_URL=postgresql+psycopg://iondu:<POSTGRES_PASSWORD>@127.0.0.1:15432/iondu_test` y correr `pytest` (sin la variable, esas pruebas se saltan) |
| Agregar un ícono | añadirlo en `frontend/scripts/generate-icons.mjs` y correr `npm run icons` |

Usuarios de prueba del frontend: `admin@iondu.demo` y `operador@iondu.demo`, contraseña `iondu2026`.

## 4. Cosas a tener en cuenta
- El contenedor en `localhost:8080` usa la imagen que se construyó la última vez; se actualiza con `docker compose up -d --build`.
- `docker compose up` exige `POSTGRES_PASSWORD` en el `.env` (cualquier valor; ver `.env.example`). Si falta, muestra un error que lo pide.
- Backend sin Docker: Python 3.12 y un entorno virtual en `backend/.venv` (`py -3.12 -m venv .venv` y `.venv\Scripts\python -m pip install -r requirements-dev.txt`). La extensión **Ruff** de VS Code formatea al guardar.
- Git avisa de que cambiará LF por CRLF en cada commit. Conviene agregar un `.gitattributes` para unificar los saltos de línea.
- Commits: formato `tipo(alcance): descripción` en español, sin menciones a IA (ver `CLAUDE.md`).
- Reglas que no se rompen: solo PostgreSQL en Supabase, todo filtrado por `id_empresa`, rutas HTTP relativas `/api/...`, `.p12` solo en memoria y la IA nunca altera ingresos.
