# IONDU · Estado del proyecto y siguientes pasos

> Resumen de traspaso. Última actualización: 24 de noviembre de 2026 (todo el frontend que tiene backend ya usa la API; ver "Frontend: conexión con la API").
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
- **Empresa y rol desde el token** (`app/api/deps.py`): se buscan en `usuario_empresa`. Un usuario puede tener
  **varias empresas**: con una sola se usa esa; con varias, el frontend elige con `X-Empresa-Id` y el backend
  comprueba la pertenencia. Sin token, `X-Empresa-Id` solo vale en desarrollo. Permiso `SoloAdministrador` para
  lo exclusivo del Administrador (`DECISIONES.md` 2.14).
- `GET /api/me/companies` (selector de empresa) y `GET /api/me` (perfil con los campos de `User` del frontend);
  flujo completo en [`API.md`](API.md), sección 5. Probado con llaves generadas en las pruebas; con Supabase real
  solo hace falta `SUPABASE_URL`.
- `PUT /api/company/certificate` (Ariana): el Administrador sube el `.p12`, que se guarda cifrado (`API.md` 6).

### Backend: ventas (fase 1)
- `POST /api/sales`, `GET /api/sales` (historial con filtros de fecha, cliente y método de pago) y
  `GET /api/sales/{id}` ([`API.md`](API.md), sección 8). Registrar exige sesión de usuario.
- En una transacción: venta, líneas, **descuento de stock** con la fila del producto bloqueada (dos ventas
  simultáneas no lo dejan en negativo) y **movimiento de inventario** `VENTA`. Precio e IVA salen del producto y
  los totales del módulo del SRI (`DECISIONES.md` 2.25).
- Falta (fase 2): emitir la factura de la venta, que requiere cambios en `factura` (sección 2.F).

### Backend: clientes
- `GET/POST /api/customers`, `GET/PATCH /api/customers/{id}` y `GET /api/customers/lookup` (autocompletar en la
  venta), según [`API.md`](API.md), sección 7. La cédula/RUC se valida con las reglas del SRI y el tipo se deduce de
  10 o 13 dígitos; el consumidor final no se guarda como cliente (`DECISIONES.md` 2.24).

### Backend: primer módulo (categorías y productos)
- Endpoints según [`API.md`](API.md): `GET/POST /api/product-categories` y `GET/POST /api/products`, `GET/PATCH /api/products/{id}`, con páginas, búsqueda y filtros (`categoryId`, `type`, `lowStock`).
- Capas: `models/` (empresa, categoría y producto, idénticos a `schema.sql`, comprobado con `alembic check`) → `repositories/` (cada repositorio recibe la empresa y todas sus consultas la filtran) → `services/` (reglas: categoría de la misma empresa, código único por empresa, el stock no se edita) → `schemas/` (validación y nombres del contrato) → `api/`.
- **Errores con formato único** (`app/core/errors.py`): `{"error": {"code", "message", "details"}}`, con mensajes de validación en español por campo.
- **Empresa provisional** (`app/api/deps.py`): solo con `APP_ENV=development` se toma del encabezado `X-Empresa-Id`; en cualquier otro entorno responde 401. Con Supabase Auth solo cambia esa función.
- Pendiente de la base: desactivar productos (falta la columna `activo`) y la restricción `UNIQUE` del código (hoy lo valida el servicio).
- Pruebas del módulo incluido el aislamiento entre empresas (207 en total en el backend). Las de base de datos usan `TEST_DATABASE_URL` (ver sección 3) y en el CI corren contra un PostgreSQL temporal.

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
- `app/core/cifrado.py` (AES-256-GCM con `MASTER_ENCRYPTION_KEY`) y `app/sri/certificado.py` (abrir el `.p12`, titular y vencimiento): listos para guardar y usar el certificado de cada empresa (`DECISIONES.md` 2.5).
- `app/sri/xades.py`: **firma XAdES-BES** como exige el SRI (RSA-SHA1), verificada en las pruebas con una librería independiente (`DECISIONES.md` 2.23).
- Sin base de datos; 117 pruebas (ninguna se conecta al SRI).
- Falta para facturar: la prueba real contra el SRI de pruebas (requiere el `.p12` y el RUC del cliente); guardar ventas y facturas en la base y los reintentos en el worker (requieren el esquema corregido).

### Backend (base)
- FastAPI con `/api/health`, hora en `America/Guayaquil`, configuración solo por variables de entorno y documentación `/api/docs` únicamente fuera de producción.
- **Conexión a PostgreSQL** con SQLAlchemy 2.1 + psycopg 3 (`app/db/session.py`): una conexión compartida con pool pequeño, zona horaria de Ecuador y *timeout* de 5 s. Los endpoints piden la sesión con `Depends(get_db)`.
- `/api/health` informa también el estado de la base: `"database": "ok" | "error" | "not_configured"` (siempre responde 200 si el proceso vive).
- **Migraciones con Alembic** (`backend/alembic/`): configurado y probado, **todavía sin migraciones**. La primera será el esquema de `database/schema.sql` cuando tenga sus correcciones.
- **Clase base de los modelos** (`app/db/base.py`) con nombres de restricciones fijos; los modelos irán en `app/models/`.
- **Ruff** revisa y formatea el código (`backend/pyproject.toml`); las migraciones nuevas se formatean solas.
- Estructura por capas acordada (patrón Repositorio del PDF): `api/` (endpoints) → `schemas/` (datos de entrada y salida) → `services/` (reglas de negocio) → `repositories/` (consultas, siempre por `id_empresa`) → `models/` (tablas). Las carpetas se crean cuando se necesitan.
- Worker con latido (`/tmp/worker-heartbeat`) y apagado limpio ante SIGTERM.
- El login ya existe (Supabase Auth); los módulos del frontend se conectan a `/api/...` uno por uno (ver "Frontend: conexión con la API").

### Base de datos (Ariana)
- **Modelos de las 17 tablas** en `backend/app/models/` con el esquema corregido: `usuario_empresa` con UUID de
  Supabase y varias empresas por usuario, `timestamptz`, `activo` y `UNIQUE` en producto, claves foráneas por
  `(id_empresa, …)` para que la base impida mezclar datos entre empresas, campos anti-duplicados en `gasto`.
- Migraciones Alembic encadenadas (agregar campos, empresa en movimientos, restricción de stock). El esquema
  completo se instala hoy con `backend/scripts/instalar_esquema_limpio.py` y los triggers con
  `instalar_funciones_triggers.py`; **falta la migración que cree todo desde cero** para Supabase.
- Auditoría de seguridad de la base (RLS, roles, permisos) y sus pendientes en [`SEGURIDAD_BD.md`](SEGURIDAD_BD.md).
- `database/schema.sql` es el esquema original (sin corregir); queda como referencia histórica.

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
- **Productos:** "+ Nuevo producto" ofrece agregar uno solo o cargar un documento (CSV o Excel) con plantilla descargable, vista previa y validación por fila. El código se genera solo y la categoría y unidad ofrecen sugerencias o texto libre. Se quitaron recetas y fabricación (ver `DECISIONES.md` 3.1.1).
- **Ventanas flotantes:** ya no se cierran si el clic empieza dentro y termina afuera.
- **Cierre de sesión:** limpia `localStorage`, `sessionStorage` y la caché del service worker (regla de `CLAUDE.md`).
- 90 pruebas del frontend.

### Frontend: conexión con la API

Estado por módulo (24/11/2026). Un servicio "real" usa `HttpClient` contra `/api/...`; uno "simulado" usa `simulateRequest` con datos de `src/app/mocks/`.

| Módulo del frontend | Estado | Servicio |
|---|---|---|
| Login, selector de empresa, `/api/me` | Real | `AuthService`, `MeApiService`, interceptor de autenticación |
| Productos y categorías (pantalla de Productos) | Real | `ProductsApiService` |
| Ventas (nueva venta e historial) | Real | `SalesService` |
| Clientes (autocompletar y crear al vender) | Real | `CustomersApiService` |
| Facturas (emitir, descargar RIDE) | Real | `BillingService` |
| Gastos, categorías de gasto y proveedores | Real | `ExpensesService`, `SuppliersApiService` |
| Movimientos (con entradas y salidas manuales), ajustes y alertas de inventario | Real | `MovementsService`, `AdjustmentsService`, `ProductsService` (caché de `/api/products`) |
| Dashboard | Real | `DashboardService` (`GET /api/dashboard`) |
| Recomendaciones | Real, por reglas sobre el dashboard (no es IA) | `RecommendationsService` |
| Empresa, configuración de facturación y firma electrónica | Real | `TenantService` |
| Bandeja de gastos por correo | Simulado (falta IMAP en el worker). Al confirmar un borrador **sí** crea un gasto real | `ExpenseInboxService` |
| Recetas y producción | Simulado (sin backend ni requisito); solo mueve el stock en memoria | `RecipesService`, `ProductionService` |
| Usuarios (gestión) | Simulado (falta el backend) | `UserDirectoryService` |
| Auditoría | Simulado (falta el backend) | `AuditService` |
| Agente de IA | Simulado (falta el sprint 4). Al confirmar una propuesta **sí** crea un gasto o un ajuste reales | `AiAgentService`, `AiNluMockService`, `AiConfigService` |

**Ventas, clientes y facturas (commits `6d5219a` y `1f143a0`):**
- `SalesService`: `GET /api/sales` (todas las páginas de 100 en 100) y `POST /api/sales`. Envía `customerId`, `items` con `productId` y `quantity` (sin precio ni IVA: los calcula el backend) y `paymentMethod`. El método de pago `tarjeta` se separó en `tarjeta_debito` y `tarjeta_credito`.
- `CustomersApiService`: `lookup`, `create` y `findOrCreate`. En Nueva venta, al escribir una cédula o RUC completo se autocompleta el cliente; si no existe, se pide el nombre y se crea al confirmar. El consumidor final es `9999999999999` (13 nueves) y no se guarda como cliente (`customerId: null`).
- `BillingService`: `POST /api/sales/{id}/invoice` y `GET /api/sales/{id}/invoice/ride`. Se eliminaron `BillingAdapterService` y `billing.mock.ts`. Estados del backend → frontend: `por_enviar` → Procesando, `por_autorizar` → Pendiente.
- Nueva venta toma los productos de `ProductsApiService`, no del `ProductsService` simulado.
- Errores: `core/utils/api-error.util.ts` extrae el mensaje del formato `{"error": {"code", "message"}}` y el interceptor de errores lo muestra en un solo aviso (los componentes no repiten el aviso). El 404 de `customers/lookup` no muestra aviso (`SKIP_ERROR_TOAST`).
- Pruebas nuevas o reescritas: `sales.service.spec.ts`, `customers-api.service.spec.ts`, `new-sale.spec.ts`, `sales-history.spec.ts`.

**Inventario, gastos, dashboard y empresa (24/11/2026):**
- `core/utils/pagination.util.ts` (`fetchAllPages`): junta todas las páginas de 100 en 100; lo usan movimientos y gastos.
- **Inventario.** `ProductsService` ya no tiene datos de ejemplo: es una caché de `/api/products` y cada pantalla llama a `refresh()` al abrirse. `MovementsService` lee `GET /api/inventory/movements` y registra entradas y salidas (`POST`); la pantalla Movimientos tiene un formulario nuevo para eso (RF-4.3). `AdjustmentsService` envía el stock real a `POST /api/inventory/adjustments` (solo Administrador) y arma su historial con los movimientos de tipo `ajuste` (stock anterior = resultante − cantidad). El backend usa `reason`; el frontend lo muestra como `reference`.
- **Gastos.** El backend guarda solo el `total` (no separa el IVA ni la observación), así que el formulario pide el total con IVA. Las categorías vienen de `/api/expense-categories` (7 predefinidas). El proveedor es opcional: con RUC o cédula se busca o crea (`SuppliersApiService`) y se autocompleta el nombre. Se agregó el número de comprobante. El método de pago `tarjeta` se separó en débito y crédito. Una categoría que no existe (por ejemplo las del agente de IA) va a "Otros gastos operativos".
- **Dashboard.** `DashboardService.summary(range)` es ahora un `Observable` de `GET /api/dashboard?from&to`; el cálculo en el navegador se eliminó. Se agregaron tarjetas de gastos por categoría y valor del inventario; el stock bajo sale del backend. Se corrigió `date-range.util.ts`: usaba `toISOString()` (UTC) y en Ecuador cambiaba de día a las 19:00, lo que enviaba un rango equivocado al backend.
- **Recomendaciones.** Mismas reglas que antes, pero sobre los indicadores reales de este mes y el anterior (dos consultas al dashboard). Como el dashboard es solo del Administrador, un Operativo ve el error 403.
- **Empresa.** `TenantService` usa `GET/PUT /api/company`, `PUT /api/company/billing-settings` y `PUT /api/company/certificate` (multipart). La pantalla Empresa ahora tiene datos generales (el RUC es de solo lectura), configuración de facturación (ambiente, establecimiento, punto de emisión, RIMPE, contabilidad, contribuyente especial) y la subida de la firma `.p12` con el estado de vencimiento. Se quitó el teléfono: el backend no lo guarda. El IVA que se muestra en Nueva venta es una constante (`TenantService.ivaRate = 0.15`, solo estimado).
- Se eliminaron `expenses.mock.ts`, `expenses-history.mock.ts`, `inventory-movements.mock.ts`, `products.mock.ts` y `tenant.mock.ts`.
- Pruebas nuevas: `expenses.service.spec.ts`, `inventory-api.service.spec.ts`, `dashboard.service.spec.ts` (incluye las reglas de recomendaciones), `tenant.service.spec.ts`. A las pruebas de los componentes que ahora usan HTTP se les agregó `provideHttpClient()` y `provideHttpClientTesting()`.

**Fase 2 (25/11/2026), resuelto en el frontend:**
- El historial de ventas muestra el estado real de la factura (viene en `Sale.invoice`), la columna "Usuario" (`createdBy`) y permite **reintentar** una factura rechazada.
- **Anular ventas** (solo Administrador, con motivo): sin factura o con factura rechazada. Con factura autorizada o en proceso se requiere nota de crédito.
- **Anular gastos** (solo Administrador, con motivo) desde el detalle del historial; los anulados no cuentan en los totales.
- **Clientes** (`/sales/customers`): listar, crear y editar con `GET/POST/PATCH /api/customers`.
- El Operativo ya no ve en el menú Dashboard, Recomendaciones ni Ajustes de inventario, y esas rutas tienen `roleGuard`.

**Verificación:** `tsc --noEmit` (app y pruebas) y `ngc --noEmit` (plantillas) pasan sin errores. **Las pruebas con `ng test` no se corrieron**: Angular CLI exige Node 22.22.3, 24.15 o 26 y la computadora usada tenía 24.8.0. Correr `npx ng test --no-watch` en `frontend/` antes de confiar en estos cambios y revisar el CI. Tampoco se probó la interfaz en el navegador contra un backend real.

### Documentación
- Requerimientos y presupuesto corregidos en Markdown (el presupuesto baja de $96,93 a $60,93 al mes).
- Guía de despliegue para quien administra el servidor.
- Lista exacta de cambios pendientes en el PDF original.

## 2. Qué falta, por orden

### Progreso del backend (estimado, 20/11/2026)

| Módulo (requisitos) | Avance | Hecho | Falta |
|---|---|---|---|
| Infraestructura | 90 % | Docker, base local, migraciones, CI, errores, Ruff | Desplegar en el VPS |
| 1. Usuarios, roles y empresa | 70 % | Token de Supabase, varias empresas por usuario y selector, rol y permiso de Administrador, `/api/me`, subir el certificado, datos y configuración de facturación de la empresa | Gestión de usuarios |
| 2. Facturación y ventas | 85 % | Identificación, clave de acceso, totales e IVA, XML validado, RIDE, cliente del SRI, flujo de emisión, cifrado del `.p12` y firma XAdES-BES, clientes, registrar ventas, facturar la venta y descargar el RIDE | Reintentos del worker, anular ventas, prueba real con el SRI (`.p12`) |
| 3. Gastos | 60 % | Categorías (7 predefinidas y propias), proveedores con RUC/cédula validados, registrar, filtrar y editar gastos | Lectura de facturas por correo (IMAP), anular gastos |
| 4. Productos e inventario | 80 % | Categorías, productos (activar/desactivar, filtro de stock bajo), movimientos por venta, entradas y salidas manuales, ajustes del Administrador, historial con stock resultante | Compra que suma inventario (RF-4.4), recetas y producción |
| 5. Dashboard | 90 % | Indicadores del período (ingresos, gastos, utilidad, ventas, ticket promedio, más vendidos, serie diaria, gastos por categoría) e inventario, solo Administrador | Nada: ya está conectado en el frontend |
| 6. Agente IA | 0 % | — | Todo (Sprint 4) |
| 7. Recomendaciones | 0 % | — | Todo (Sprint 5) |

### Qué necesita el backend de cada uno

| # | Quién | Qué | Desbloquea en el backend | Urgencia |
|---|---|---|---|---|
| 1 | Ariana | ✅ Modelos con el esquema corregido. Falta: migración que cree todo desde cero y los pendientes de `SEGURIDAD_BD.md` | Desplegar en Supabase | Media |
| 2 | Equipo | Crear el proyecto de Supabase y pasar URL y claves por un canal seguro | Login real: validar el token y tomar la empresa del usuario | Alta |
| 3 | Equipo | Decidir el tipo de producto y si Recetas/Producción entran en el MVP | Cerrar productos; tablas de recetas si entran | Media |
| 4 | Denisse | ✅ Productos, ventas, clientes y facturas conectados. Falta conectar el resto (ver "Frontend: conexión con la API") | Pantallas con datos reales | Media |
| 5 | Denisse | ✅ Consumidor final con 13 nueves | Evitar facturas rechazadas | — |
| 6 | Denisse | ✅ Login de Angular con Supabase Auth | Enviar el token al backend | — |
| 7 | Cliente | Certificado `.p12`, RUC del emisor, VPS y dominio | Probar la firma y el envío en el SRI de pruebas (el código ya está listo); desplegar | Pedirlo ya |

El código de facturación está listo para probarse contra el SRI apenas llegue el `.p12`; guardar ventas y facturas espera el esquema corregido de Ariana.

### A. Cosas rápidas
1. Confirmar que el CI de GitHub (pestaña **Actions**) esté en verde tras el último push.
2. Correr `/impeccable init` una vez en Claude Code, y decidir si se mantiene el hook que revisa la interfaz al editar.
3. Reemplazar el logo vectorizado cuando exista el SVG original.

### B. Frontend (lo que queda)
1. Revisión visual, pantalla por pantalla y en móvil, de Gastos, Inventario, Agente IA y Configuración. Se comprobó que no se desbordan y que cumplen accesibilidad, pero falta revisar su aspecto con ojo de diseño.
2. Pulido con `impeccable` (`/impeccable init` y luego `audit` y `polish`).
3. Probar la instalación de la PWA y el service worker en Chrome.
4. Ya están conectados todos los módulos que tienen backend. Lo que sigue simulado no tiene dónde guardarse todavía: gestión de usuarios, auditoría, bandeja de gastos por correo (IMAP), agente de IA, y recetas y producción (ver la tabla "Frontend: conexión con la API").
5. Pasar `Product.id`, `User.tenantId` y los demás IDs de `string` a `number`, como pide `API.md` sección 9 (hoy los servicios convierten con `String(...)` y `Number(...)`).
6. ✅ Ocultar en el menú lo que el backend restringe al Administrador (dashboard, recomendaciones y ajustes de inventario).
7. Nueva venta: la vista previa del IVA usa una tasa fija del 15 %; mostrar el IVA real por producto (`vatPercentageCode`) y soportar líneas de concepto libre.
8. Editar gastos y proveedores (el backend ya tiene `PATCH`). ✅ Anular gastos y ✅ listar y editar clientes.
9. Probar todo en el navegador contra el backend real con datos demo (`backend/scripts/cargar_datos_demo.py`), con un Administrador y un Operativo.
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

**Tabla `factura` (para la fase 2 de ventas):**
1. `numero_comprobante` es único en todo el sistema: la segunda empresa no podría emitir su factura
   `001-001-000000001`. Debe ser único por empresa (agregar `id_empresa` a `factura`).
2. Faltan columnas para el resultado del SRI: número y fecha de autorización, motivos de rechazo (JSONB) e
   intentos de envío.
3. `detalle_venta` no guarda la tarifa de IVA de cada línea (hace falta para el XML y para las líneas sin producto).
4. Dónde se configuran el establecimiento, el punto de emisión, el ambiente y el secuencial de cada empresa.

**Por decidir en equipo:** los valores del tipo de producto, y si Recetas y Producción entran en el MVP (si entran, hay que agregarlas a los requisitos y crear sus tablas).

**Contrato de la API:** en [`API.md`](API.md), empezando por productos (ya implementados en el backend). El JSON usará los nombres que ya usa el frontend (`sku`, `name`, `salePrice`…) y el backend los traduce a las columnas de la base. Así, en el frontend basta con cambiar `simulateRequest(...)` por llamadas reales en cada servicio.

### G. Pendientes del backend para el frontend
Detectados al conectar Ventas y Facturación (24/11/2026). Cada uno bloquea una función de la interfaz:

| # | Falta en el backend | Efecto hoy en el frontend |
|---|---|---|
| 1 | ✅ Resumen de la factura dentro de `Sale` | Conectado en el historial (25/11/2026) |
| 2 | ✅ Reintentar una factura rechazada | Botón "Reintentar emisión" en el detalle. Falta corregir la cédula o RUC desde ahí (se hace en Clientes) |
| 3 | ✅ `createdBy` en `Sale` | Columna "Usuario" en el historial |
| 4 | ✅ Anular ventas (RF-2.7) | Botón "Anular venta" para el Administrador |
| 5 | Prueba real con el SRI de pruebas (requiere el `.p12` y el RUC del cliente) | Las facturas no se han autorizado contra el SRI real |
| 6 | Reintentos del worker para facturas en `por_enviar` o `por_autorizar` | Esas facturas quedan "En proceso" hasta que el worker las resuelva; la pantalla no se actualiza sola |

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

**Probar todo el sistema en local (frontend contra el backend real):**
1. Node 22.22.3 o superior, 24.15 o superior, o 26 (el Angular CLI no corre con menos). Luego `cd frontend && npm ci && npx ng test --no-watch`.
2. Con Docker encendido: copiar `.env.example` a `.env` y completar `POSTGRES_PASSWORD`, `APP_ENV=development`, las tres conexiones y `DEV_USER_ID=11111111-1111-1111-1111-111111111111`. Luego `docker compose up --build -d`.
3. Preparar la base (desde `backend/`, con las variables de conexión del README): `scripts\bootstrap_local_auth.py`, `alembic upgrade head` y `python -m scripts.cargar_datos_demo` (cafetería con un mes de ventas).
4. El login usa **Supabase real** (el `.env` del frontend apunta a su proyecto), no usuarios de ejemplo. La base local no conoce a ese usuario: tras entrar la API responde `NO_COMPANY`. Se soluciona con `python -m scripts.asignar_usuario_local --usuario <uuid de Supabase> --nombre "Nombre" [--rol Operativo]`. Para probar el rol Operativo hay que repetirlo con otro usuario.
5. Abrir http://localhost:8080 y recorrer: venta con cliente nuevo y con consumidor final (baja el stock), emitir factura (sin `.p12` debe dar un error claro), entrada, salida y ajuste de inventario, gasto con y sin proveedor, dashboard con distintos períodos, y configuración de la empresa. Con el Operativo, Dashboard, Recomendaciones, Ajustes y Empresa deben responder 403.
6. Para separar fallos del frontend de los del backend, probar la API sola en http://localhost:8080/api/docs con los encabezados `X-Empresa-Id` y `X-Usuario-Id`.

Ya no existen los usuarios de ejemplo `admin@iondu.demo` y `operador@iondu.demo`: el login simulado se reemplazó por Supabase Auth.

## 4. Cosas a tener en cuenta
- El contenedor en `localhost:8080` usa la imagen que se construyó la última vez; se actualiza con `docker compose up -d --build`.
- `docker compose up` exige `POSTGRES_PASSWORD` en el `.env` (cualquier valor; ver `.env.example`). Si falta, muestra un error que lo pide.
- Backend sin Docker: Python 3.12 y un entorno virtual en `backend/.venv` (`py -3.12 -m venv .venv` y `.venv\Scripts\python -m pip install -r requirements-dev.txt`). La extensión **Ruff** de VS Code formatea al guardar.
- Git avisa de que cambiará LF por CRLF en cada commit. Conviene agregar un `.gitattributes` para unificar los saltos de línea.
- Commits: formato `tipo(alcance): descripción` en español, sin menciones a IA (ver `CLAUDE.md`).
- Reglas que no se rompen: solo PostgreSQL en Supabase, todo filtrado por `id_empresa`, rutas HTTP relativas `/api/...`, `.p12` solo en memoria y la IA nunca altera ingresos.
