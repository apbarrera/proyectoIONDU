# Correcciones pendientes en `Proyecto Final Ing. Software I (2).pdf`

El PDF no se puede editar directamente. Esta es la lista exacta de cambios para aplicar en el documento fuente
(Word, Docs u otro) y volver a exportarlo. Los números de línea son del texto extraído del PDF, solo como referencia.

## A. Base de datos: unificar a PostgreSQL

El documento menciona MySQL en varios lugares aunque el motor es PostgreSQL (Tabla 1, RNF-14 y la sección 2.4).

| Dónde | Dice | Debe decir |
|---|---|---|
| Patrón Repositorio (~l. 1750) | "base de datos MySQL Multi-Tenant" | "base de datos PostgreSQL Multi-Tenant" |
| Patrón Repositorio (~l. 1807) | `MySQLProductoRepository` | `PostgresProductoRepository` |
| Patrón Repositorio (~l. 1837) | `new MySQLRepo()` | `new PostgresRepo()` |
| Diagramas de secuencia CU-01, 02, 04, 05, 06, 07, 08 (~l. 2251, 2300, 2422, 2469, 2523, 2565) | "Base de Datos: MySQL (...)" | "Base de Datos: PostgreSQL (...)" |
| CU-08 (~l. 2639) | "base de datos MySQL" | "base de datos PostgreSQL" |
| Modelado de la BD, introducción (~l. 2747) | "MySQL" | "PostgreSQL" |
| Estrategia de índices (~l. 3151) | "base de datos MySQL" | "base de datos PostgreSQL" |
| Estrategia de índices (~l. 3154) | `INT AUTO_INCREMENT` | `BIGINT GENERATED ALWAYS AS IDENTITY` (o `UUID`) |
| Secuencia de login (~l. 2275) | consultas con `?` | parámetros de PostgreSQL (`$1`, `$2`) o simplemente "consulta parametrizada" |
| Todas las tablas | `INT … Auto Increment` | `BIGINT … IDENTITY` o `UUID` |
| Tabla `usuario` | `ENUM('ACTIVO','INACTIVO')` | `TEXT` con `CHECK` o tipo `ENUM` de PostgreSQL |
| Tabla `empresa` | `JSON` | `JSONB` |

## B. Autenticación: decidir entre Supabase Auth o sistema propio

El presupuesto usa Supabase Auth, pero el diagrama de login (~l. 2244–2281) y la tabla `usuario` (~l. 2902–2912) usan contraseñas propias con `contrasena_hash` e IDs `INT AUTO_INCREMENT`. Supabase Auth identifica usuarios con **UUID** y guarda sus propias contraseñas.

**Recomendación:** Supabase Auth para la identidad.

- Eliminar `contrasena_hash` de la tabla `usuario` y de la clase `Usuario` (~l. 1609).
- Reemplazar la tabla `usuario` por `usuario_empresa (id_usuario UUID PK → auth.users.id, id_empresa, id_rol, nombre, estado)`.
- Rehacer el diagrama de secuencia de CU-01: el frontend autentica contra Supabase Auth, recibe un JWT y el backend lo valida; luego carga el rol y la empresa desde `usuario_empresa`.
- Quitar `verificarHash()` de la matriz de trazabilidad dinámica (~l. 2602).
- RNF-06 queda como está en [`REQUISITOS.md`](REQUISITOS.md).

## C. Firma electrónica y credenciales (tabla `empresa`)

| Campo | Dice (~l. 2889–2892) | Debe decir |
|---|---|---|
| `firma_electronica` | `VARCHAR(255)`: "Ruta o hash del archivo .p12" | `p12_cifrado BYTEA` (o ruta a un bucket privado de Supabase Storage) y `p12_clave_cifrada BYTEA`. Cifrado AES-GCM con `MASTER_ENCRYPTION_KEY`. Un *hash* no sirve para firmar y una ruta local ata el sistema a un servidor. |
| `datos_facturacion_electronica` | `JSON`: "Configuración y credenciales del SRI" | `JSONB` **sin credenciales**; las credenciales van cifradas. |
| (nuevo) | — | `p12_fecha_vencimiento DATE`, para la alerta de caducidad (RNF-25). |
| (nuevo) | — | Credenciales IMAP por empresa, cifradas (`imap_config_cifrada BYTEA`). |

## D. Aislamiento multi-tenant

En "Arquitectura Multi-Tenant (Aislamiento por Registro)" agregar: además del filtro por `id_empresa` en el código, se activa **Row Level Security (RLS)** en PostgreSQL como segunda capa de defensa (RNF-23). Cada tabla con `id_empresa` lleva una política que compara con la empresa del usuario autenticado.

## E. Idempotencia de la lectura de correos

En la tabla `gasto` (o una tabla auxiliar) agregar `message_id_correo` y `clave_acceso` con restricción `UNIQUE` por empresa, para que un reinicio del worker no duplique gastos (RF-3.2).

## F. Diagrama y texto de despliegue (Figura 28, ~l. 2707–2741)

Rehacer el diagrama y ajustar el texto:

- Eliminar Vercel, DigitalOcean y cualquier servicio gestionado de alojamiento.
- Mostrar un **VPS del cliente** con Docker y un proxy inverso (HTTPS) que enruta a tres contenedores: `web` (Nginx + PWA), `api` (FastAPI) y `worker` (misma imagen que `api`).
- Punto 2: "la petición llega por HTTPS al proxy inverso del servidor, que la dirige al contenedor `web`; las rutas `/api` se reenvían al contenedor `api`".
- Punto 3: los módulos del backend corren en el contenedor `api`.
- Punto 5: el proceso periódico es el contenedor `worker`.
- Fuera del VPS quedan: Supabase (PostgreSQL, Auth, Storage), SRI, OpenAI, Resend y el servidor IMAP.

## G. Requerimientos no funcionales

Reemplazar la tabla por la de [`REQUISITOS.md`](REQUISITOS.md): cambian RNF-03, RNF-06, RNF-14 y RNF-16, y se agregan RNF-21 a RNF-25.

Además, en la sección 2.3 y 2.4:

- Backend: "Python con **FastAPI**".
- Agregar "Docker y Docker Compose" a las tecnologías y a las restricciones.
- "Supabase: base de datos, autenticación y almacenamiento".

## H. Presupuesto

Reemplazar la tabla por la de [`PRESUPUESTO.md`](PRESUPUESTO.md).

## I. Riesgos (opcional)

Agregar a la matriz:

- **Pérdida de la `MASTER_ENCRYPTION_KEY`** → se pierden todos los certificados cifrados. Mitigación: respaldo en un gestor de contraseñas. Impacto Alto.
- **Vencimiento del certificado `.p12` del cliente** → el cliente deja de poder facturar. Mitigación: alerta de caducidad (RNF-25).
- **Fallo del VPS del cliente** → indisponibilidad. Mitigación: snapshots, healthchecks y `restart: unless-stopped`.
