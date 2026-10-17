# IONDU · Estado del proyecto y siguientes pasos

> Resumen de traspaso. Última actualización: 17 de octubre de 2026 (tras unir Ventas con Facturación y la auditoría de accesibilidad).
> Documentos relacionados: [`REQUISITOS.md`](REQUISITOS.md) · [`PRESUPUESTO.md`](PRESUPUESTO.md) · [`DESPLIEGUE.md`](DESPLIEGUE.md) · [`CORRECCIONES_PDF.md`](CORRECCIONES_PDF.md)

## 1. Qué está hecho

### Infraestructura y repositorio
- Monorepo ordenado: `frontend/`, `backend/` y `docs/`.
- Docker con tres servicios: `web` (Angular + Nginx), `api` (FastAPI) y `worker`. `docker-compose.yml` es compatible con Coolify: solo `web` es público; `api` y `worker` usan `expose`.
- `.env.example` sin secretos. El `.gitignore` excluye `.env`, `*.p12`, `*.pfx` y `*.zip`.
- CI en GitHub Actions: pruebas del frontend, pruebas del backend (dentro de Docker) y construcción de las imágenes.
- `CLAUDE.md` con las reglas del proyecto y el formato obligatorio de commits.

### Backend (esqueleto)
- FastAPI con `/api/health`, hora en `America/Guayaquil`, configuración solo por variables de entorno y documentación `/api/docs` únicamente fuera de producción.
- Worker con latido (`/tmp/worker-heartbeat`) y apagado limpio ante SIGTERM.
- 4 pruebas.
- **Todavía sin lógica de negocio ni base de datos.**

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
2. Esquema multi-tenant con migraciones Alembic (`empresa`, `usuario_empresa`, `rol`, …) y RLS por `id_empresa`.
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

## 3. Cómo trabajar en el proyecto

| Tarea | Comando |
|---|---|
| Levantar todo con Docker | `docker compose up -d --build` y abrir http://localhost:8080 |
| Desarrollar el frontend | `cd frontend && npm start` (http://localhost:4200) |
| Pruebas del frontend | `cd frontend && npx ng test --no-watch` |
| Pruebas del backend | `docker build --target test backend` (no hace falta Python local) |
| Agregar un ícono | añadirlo en `frontend/scripts/generate-icons.mjs` y correr `npm run icons` |

Usuarios de prueba del frontend: `admin@iondu.demo` y `operador@iondu.demo`, contraseña `iondu2026`.

## 4. Cosas a tener en cuenta
- El contenedor en `localhost:8080` usa la imagen que se construyó la última vez; se actualiza con `docker compose up -d --build`.
- Git avisa de que cambiará LF por CRLF en cada commit. Conviene agregar un `.gitattributes` para unificar los saltos de línea.
- Commits: formato `tipo(alcance): descripción` en español, sin menciones a IA (ver `CLAUDE.md`).
- Reglas que no se rompen: solo PostgreSQL en Supabase, todo filtrado por `id_empresa`, rutas HTTP relativas `/api/...`, `.p12` solo en memoria y la IA nunca altera ingresos.
