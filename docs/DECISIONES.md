# IONDU · Decisiones del proyecto

> Registro de las decisiones tomadas y **por qué**. Sirve para no volver a discutir lo ya resuelto y para
> que cualquier persona nueva entienda el contexto. El estado y los pendientes están en [`ESTADO.md`](ESTADO.md).
> Si una decisión cambia, se actualiza aquí con la fecha y el motivo.

## 1. Despliegue e infraestructura

### 1.1 Todo en Docker, sobre un VPS del cliente, administrado con Coolify
- **Decisión:** el sistema se entrega como contenedores Docker (`web`, `api`, `worker`) descritos en un único
  `docker-compose.yml`. Se despliega en un **VPS que administra el cliente**, con **Coolify** como panel
  (proxy Traefik, HTTPS con Let's Encrypt, despliegue desde GitHub y variables de entorno).
- **Por qué:**
  - El cliente indicó que solo necesita que el sistema esté en Docker y que él se encarga del servidor.
  - Un VPS único es más barato y simple que servicios separados (Vercel + DigitalOcean), y el proyecto es un MVP.
  - Docker hace que el sistema corra igual en local, en pruebas y en producción.
- **Consecuencias:**
  - Se eliminan del presupuesto Vercel, DigitalOcean App Platform, sus tareas programadas y su gestor de secretos.
    El total mensual baja de $96,93 a $60,93 (el VPS lo paga el cliente). Ver [`PRESUPUESTO.md`](PRESUPUESTO.md).
  - Funciona con cualquier servidor que tenga Docker; Coolify es la opción recomendada, no obligatoria.
    Guía en [`DESPLIEGUE.md`](DESPLIEGUE.md).
  - Requisitos del VPS: Ubuntu 24.04, **mínimo 2 vCPU y 4 GB de RAM** (compilar Angular consume memoria),
    puertos 22, 80 y 443 abiertos y un dominio apuntando al servidor.

### 1.2 Un solo recurso Docker Compose en Coolify
- **Decisión:** el compose es la única fuente de verdad (Build Pack "Docker Compose", ruta `/docker-compose.yml`).
- **Por qué:** se reproduce igual en local, y la API y el worker comparten imagen y variables.
- **Costo asumido:** cada push redespliega todo el stack. Es aceptable para un MVP; si hace falta, el frontend se
  separa como aplicación aparte.

### 1.3 Solo el servicio `web` es público; `expose` en vez de `ports`
- **Decisión:** `api` y `worker` usan `expose` y no publican puertos. Nginx (en `web`) reenvía `/api/*` a `api:8000`.
- **Por qué:** Docker se salta el firewall (UFW) cuando se publican puertos con `ports:`, así que cualquier puerto
  publicado queda abierto a internet. Con `expose`, solo el proxy de Coolify llega a los servicios.
- **Consecuencia:** para probar en local se usa `docker-compose.override.yml`, que publica `8080`. **Coolify nunca
  lo lee** (solo lee `docker-compose.yml`).
- No se declaran redes propias: Coolify crea una red aislada por stack y conecta Traefik solo a los servicios con dominio.

### 1.4 Contenedores sin estado (sin volúmenes)
- **Decisión:** nada se guarda en el disco de los contenedores. Archivos, PDF, XML e imágenes van a un
  almacenamiento de objetos con **API S3** (variables `STORAGE_*`): Supabase Storage por su endpoint S3 en producción
  y **SeaweedFS** (servicio `storage` de `docker-compose.override.yml`) en local.
- **Cambio (25/11/2026):** se reemplazó el cliente de Supabase (`supabase-py`) por `boto3`. El mismo código sirve
  para cualquier proveedor S3 y el sistema corre completo en local. Se eligió SeaweedFS porque MinIO dejó de
  publicar imágenes de Docker. En desarrollo la API crea el bucket si falta; en producción se crea privado al preparar
  el ambiente. Rutas: `empresas/{id}/facturas/{id}/ride.pdf`; si el archivo no se puede leer, el RIDE se reconstruye
  desde el XML autorizado.
- **Por qué:** un contenedor se puede recrear en cada despliegue sin perder datos, y los respaldos se simplifican.
- **Consecuencia:** se descartó el volumen de certificados que traía la propuesta inicial.

### 1.5 Mismo origen: el frontend llama a `/api/...`
- **Decisión:** todas las peticiones HTTP usan rutas relativas (`/api/...`), sin URLs absolutas. En desarrollo,
  `proxy.conf.json` reenvía `/api` a `localhost:8000`.
- **Por qué:** sin CORS, cookies más simples y una PWA más estable.

### 1.6 Imagen única para la API y el worker
- **Decisión:** un solo `Dockerfile` (`backend/`); el worker solo cambia el comando (`python -m app.worker`).
- **Por qué:** una compilación, las mismas dependencias y menos mantenimiento.
- La compilación incluye un *target* `test` que ejecuta Ruff y `pytest`: si algo falla, falla la construcción.
- **Cambio (21/10/2026):** el `worker` ya no declara `image: iondu-backend:latest`. Como `api` y `worker` tenían
  `build:` y el mismo nombre de imagen, al construirse en paralelo a veces fallaba con `image ... already exists`
  (pasaba en unas máquinas sí y en otras no). Ahora cada servicio construye su imagen desde el mismo `Dockerfile`;
  la caché de Docker reutiliza todas las capas, así que no tarda el doble ni ocupa el doble.

### 1.7 Nginx y la PWA
- `ngsw-worker.js`, `ngsw.json` e `index.html` se sirven **sin caché** (si se cachean, los usuarios quedan atascados
  en versiones viejas). Los archivos con hash llevan caché de un año (`immutable`).
- El service worker exige HTTPS, que cubre Traefik. `/api/**` se excluye de la navegación del service worker.
- **Cambio (25/10/2026):** el proxy usa `location ^~ /api/`. Sin el `^~`, Nginx daba prioridad a la regla de
  estáticos por extensión (`.json`, `.png`, …) y rutas como `/api/openapi.json` respondían 404 desde el frontend
  (y lo mismo habría pasado con cualquier endpoint futuro que termine en esas extensiones).

### 1.8 Integración continua
- **GitHub Actions** en cada push y pull request: pruebas y build del frontend, revisión con Ruff y pruebas del
  backend (en Docker) y construcción de las imágenes. Opcional a futuro: construir las imágenes en Actions y
  publicarlas en GHCR para que el VPS solo las descargue.
- **Las imágenes se construyen con `docker compose -f docker-compose.yml build`** (21/10/2026), sin el override.
  **Por qué:** el CI debe comprobar lo mismo que despliega Coolify, y el override (solo local) exige variables del
  `.env` que el CI no tiene; al principio eso dejó el CI en rojo.

### 1.9 PostgreSQL local para desarrollo
- **Decisión (21/11/2026):** API, worker y Alembic utilizan conexiones PostgreSQL independientes mediante `DATABASE_URL`, `WORKER_DATABASE_URL` y `MIGRATION_DATABASE_URL`, respectivamente. Las tres deben configurarse explícitamente en el entorno, también en desarrollo local.
- **Por qué:** se separan los privilegios de ejecución de la API, el worker y las migraciones. Esto permite aplicar RLS y el principio de mínimo privilegio sin compartir una cuenta administrativa.
- Se publica solo en `127.0.0.1:15432` (no se ve desde la red). Se eligió 15432 porque en la máquina de desarrollo
  ya había PostgreSQL instalados en 5432, 5433 y 5434.
- La contraseña no está en el repositorio: se lee de `POSTGRES_PASSWORD` en el `.env`, que es obligatoria.
- Usa un volumen (`db-data`) para no perder los datos al apagar el contenedor. Es la única excepción a la decisión
  1.4, y solo en local: Coolify no lee el override.
- **Cambio (26/11/2026): mismos roles que producción.** En local la API se conecta como `iondu_app` y el worker como
  `iondu_worker` (`scripts/configurar_roles_locales.py` les da LOGIN con la contraseña del `.env`); solo las
  migraciones usan `iondu`. Antes la API local entraba como administrador y no ejercitaba ni el RLS ni los permisos:
  un error de permisos de la gestión de usuarios solo apareció al probar con el rol real.
- **Los permisos viven en las migraciones** (`a3c5e7f9b104` y las de usuarios): antes los `GRANT` se aplicaban a mano
  en Supabase y un ambiente nuevo quedaba sin permisos. Lectura e inserción por tabla y `UPDATE` solo de las columnas
  que el código modifica; las tablas sin funcionalidad no reciben nada. Una funcionalidad nueva que escriba otra
  columna necesita su migración de permisos. Verificado sobre una base vacía recorriendo todos los endpoints de
  escritura como `iondu_app` y un ciclo del worker como `iondu_worker`.
- **Instalación desde cero:** la primera migración crea el marcador `auth.users` si falta, así que una base vacía
  queda lista solo con `alembic upgrade head` (se eliminó `scripts/bootstrap_local_auth.py`).

## 2. Backend y datos

### 2.1 FastAPI
- **Decisión:** el backend es Python con **FastAPI** (el documento original decía solo "Python / Flask / FastAPI").
- **Por qué:** es asíncrono, valida con Pydantic y genera la especificación OpenAPI automáticamente.
- `/api/health` debe existir siempre (healthcheck de Docker y Coolify). La documentación interactiva
  (`/api/docs`) solo existe fuera de producción.

### 2.2 Base de datos: solo PostgreSQL en Supabase
- **Decisión:** PostgreSQL administrado por **Supabase Cloud**. Está prohibido usar sintaxis o tipos de MySQL.
- **Por qué:** el documento mezclaba MySQL y PostgreSQL. Se unifica a PostgreSQL, que es lo que ya está en el
  presupuesto y en los requisitos (RNF-14).
- **Supabase se contrata en la nube, no se aloja en el VPS:** son unos diez contenedores y el equipo pasaría a ser
  responsable de sus respaldos.
- Conexión **siempre por el Session Pooler** (puerto 5432). La conexión directa es solo IPv6 y Docker en un VPS suele
  salir por IPv4. Con el Transaction Pooler (6543) hay que desactivar los *prepared statements*.
- La región de Supabase debe estar cerca del VPS para no sumar latencia.

### 2.3 Autenticación propia (reemplaza a Supabase Auth)
- **Decisión (25/11/2026):** la identidad la gestiona el backend. Tabla `usuario` (correo único en minúsculas, hash
  argon2id, bloqueo por intentos) y `sesion_refresh` (hash SHA-256 de cada token de renovación). `usuario_empresa`
  sigue guardando empresa, rol y estado; su FK apunta ahora a `usuario.id` (migración `e5b1c7a9d203`, que conserva
  los UUID de los usuarios existentes).
- **Por qué:** permite levantar y probar todo el sistema en local sin un proyecto de Supabase, quita una dependencia
  externa del login y deja el control de la sesión (bloqueo, revocación) en el backend. La base de datos y Storage
  pueden seguir en Supabase: solo cambia la autenticación.
- **Antes (27/10/2026 a 25/11/2026):** Supabase Auth, con el JWT verificado por las llaves públicas de Supabase
  (JWKS). Se retiró junto con `@supabase/auth-js` del frontend.
- **Tokens:**
  - **Acceso:** JWT `ES256` firmado con `AUTH_JWT_PRIVATE_KEY` (EC P-256; solo la API la tiene, el worker no),
    15 minutos (`AUTH_ACCESS_TOKEN_MINUTES`), `iss=iondu`, `aud=iondu-api`, 30 s de margen de reloj. Solo se acepta
    `ES256`: bloquea el token sin firma (`alg: none`) y la confusión con `HS256`; hay pruebas de ambos ataques.
  - **Renovación:** valor aleatorio de 32 bytes en la cookie `iondu_refresh` (`HttpOnly`, `SameSite=Strict`,
    `Path=/api/auth`, `Secure` fuera de desarrollo), 7 días (`AUTH_REFRESH_TOKEN_DAYS`). Se rota en cada uso; si
    llega uno ya rotado después de 30 s de gracia, alguien lo copió y se cierran todas las sesiones del usuario.
  - La llave se genera con `python -m scripts.generar_llave_jwt`; cada ambiente tiene la suya y cambiarla cierra
    todas las sesiones.
- **Contraseñas:** argon2id (parámetros por defecto de `argon2-cffi`), mínimo 10 caracteres. Tras 5 intentos
  fallidos, la cuenta se bloquea 15 minutos. El mensaje es el mismo exista o no el correo, y se calcula un hash
  ficticio para que el tiempo de respuesta no lo delate.
- **Permisos en la base:** `iondu_app` lee `usuario` y solo modifica `password_hash`, `intentos_fallidos` y
  `bloqueado_hasta`; en `sesion_refresh` lee, inserta, borra y solo modifica `rotada_en` y `revocada_en`. Estas
  tablas no usan RLS por empresa porque el login busca al usuario antes de saber quién es. El worker no tiene
  acceso. Crear usuarios exige la credencial de migraciones (`scripts/crear_usuario.py`).
- **Frontend:** el token de acceso vive solo en memoria (nunca en `localStorage`); al recargar la página, la sesión
  se recupera con la cookie. El interceptor renueva el token si está por vencer o si recibe `401 TOKEN_EXPIRED` y
  repite la petición una vez; si no puede renovarlo, cierra la sesión y lleva al login.
- **Pendiente:** limitar intentos por IP en Nginx (hoy el bloqueo es por cuenta), gestión de usuarios desde la
  aplicación y "olvidé mi contraseña" (requiere enviar correos).

### 2.4 Multi-tenant: filtro por `id_empresa` **y** RLS
- **Decisión:** todo endpoint y consulta filtra estrictamente por `id_empresa`, y además se activa **Row Level
  Security** en PostgreSQL como segunda capa.
- **Por qué:** en un SaaS de facturación, un solo `WHERE` olvidado filtraría datos de otra empresa.
- Se identifica al tenant por el JWT, no por subdominio (los subdominios por tenant requieren certificado *wildcard*).

### 2.5 Certificados `.p12`: cifrados, nunca en disco
- **Decisión:** cada `.p12` y su contraseña se guardan **cifrados (AES-GCM)** con una `MASTER_ENCRYPTION_KEY` que vive
  solo como variable de entorno. Al firmar se descifran **solo en memoria**.
- **Por qué:** un *hash* no sirve para firmar, y una ruta a disco local ata el sistema a un servidor y complica los
  respaldos. Tampoco se guardan credenciales en JSON en texto plano.
- **Riesgo conocido:** si se pierde la `MASTER_ENCRYPTION_KEY`, se pierden todos los certificados de los clientes.
  Debe respaldarse además en un gestor de contraseñas.
- Hay que alertar antes de que un certificado venza: cuando pasa, el cliente deja de poder facturar.
- Las credenciales IMAP son por empresa y también van cifradas en la base, no en el `.env`.
- **Implementado (27/10/2026):** `app/core/cifrado.py` con AES-256-GCM (`cryptography`). Lo guardado tiene el
  formato `[versión][nonce de 12 bytes][cifrado + etiqueta]`:
  - nonce aleatorio nuevo en cada cifrado (reusarlo con la misma llave rompe GCM);
  - un **contexto** amarrado al dato (por ejemplo `empresa:7:p12` y `empresa:7:p12_clave`): un valor copiado a otra
    empresa u otro campo no se descifra;
  - GCM detecta cualquier alteración; el byte de versión permite cambiar de llave o algoritmo en el futuro.
  - La llave se genera con `python -m app.core.cifrado`; cómo cuidarla está en `DESPLIEGUE.md`.
- `app/sri/certificado.py` abre el `.p12` en memoria, valida la contraseña y exige llave RSA (la usa la firma del
  SRI), y da el titular y la fecha de vencimiento: `por_vencer()` (30 días o menos, RNF-25) y `vencido()`.
- **Guardar el certificado (31/10/2026, Ariana):** `PUT /api/company/certificate` (solo Administrador) recibe el
  `.p12` y su contraseña, los valida en memoria (máximo 5 MiB, contraseña correcta, no vencido) y guarda ambos
  cifrados con `cifrado.py` en `empresa` (base64 del dato cifrado completo), más `certificado_fecha_vencimiento`.
  Se descartó el segundo módulo de cifrado (`encryption.py`); las columnas `certificado_nonce`,
  `certificado_tag`, `certificado_password_nonce` y `certificado_password_tag` quedaron sin uso.

### 2.6 Worker simple, sin Redis ni Celery (por ahora)
- **Decisión:** un ciclo con una cola en PostgreSQL (`SELECT … FOR UPDATE SKIP LOCKED`), una sola instancia.
- **Por qué:** cubre la lectura IMAP, los reintentos con el SRI y las alertas de inventario sin agregar infraestructura.
  Si crece el volumen, se pasa a Redis con arq o Celery.
- Debe ser **idempotente** (`Message-ID` del correo y clave de acceso con restricción `UNIQUE`), manejar SIGTERM y
  escribir un latido que usa el healthcheck.

### 2.7 Zona horaria `America/Guayaquil`
- Para fechas y comprobantes del SRI; es crítica para la fecha de emisión y la clave de acceso.

### 2.8 Configuración solo por variables de entorno
- Nada escrito en el código. `.env.example` es la plantilla sin secretos; `.env`, `*.p12`, `*.pfx` y `*.zip`
  están en `.gitignore`. Los secretos reales se cargan en el panel del despliegue.
- La `service_role key` de Supabase solo en el backend, nunca en Angular.

### 2.9 Reglas de negocio no negociables
- La IA nunca crea ni altera ingresos; estos solo entran por facturación electrónica o venta manual.
- Toda acción de la IA sobre inventario o gastos requiere confirmación explícita del usuario.
- El dashboard financiero es exclusivo del rol Administrador.

### 2.10 Acceso a datos: SQLAlchemy 2 sincrónico + psycopg 3
- **Decisión (20/10/2026):** SQLAlchemy en modo sincrónico (no `async`), con el driver psycopg 3.
- **Por qué:** es más simple de escribir, leer y depurar. FastAPI ejecuta los endpoints normales (`def`) en un
  grupo de hilos, lo que alcanza para los 100 usuarios concurrentes de RNF-04.
- Una sola conexión compartida (`app/db/session.py`) con pool de 5 (+5 extra) por proceso: el Session Pooler de
  Supabase limita las conexiones y la API corre con 2 procesos de uvicorn. Cada conexión usa la zona horaria de
  Ecuador y se rinde a los 5 s si la base no responde.
- `/api/health` responde siempre 200 si el proceso vive (lo usa el healthcheck de Docker) e informa aparte el estado
  de la base (`database: ok | error | not_configured`). Así, una caída de Supabase no hace que Docker dé por muerta la API.

### 2.11 Migraciones con Alembic
- **Decisión (21/10/2026):** los cambios a la base se hacen con **migraciones de Alembic** (`backend/alembic/versions/`),
  no volviendo a exportar `schema.sql`. Cada uno actualiza su base con `alembic upgrade head`; Supabase, igual.
- **Por qué:** se aplica solo lo nuevo, sin borrar datos, y se sabe en qué versión está cada base (`alembic current`).
  En producción, con datos reales, es la única forma segura.
- La primera migración será el esquema de `database/schema.sql` una vez corregido (ver `ESTADO.md`, sección 2.F).
  `env.py` lee la dirección de `MIGRATION_DATABASE_URL` (nunca de `DATABASE_URL` ni de `alembic.ini`) y **nunca propone borrar una tabla que no tenga
  modelo**: el `--autogenerate` solo crea o modifica; un `DROP TABLE` se escribe a mano.
- Los modelos heredan de `Base` (`app/db/base.py`), que fija los nombres de las restricciones con el mismo estilo de
  PostgreSQL (`producto_id_empresa_fkey`, `empresa_ruc_key`); sin eso, Alembic no puede modificarlas después.
- Las migraciones se crean en local y se aplican desde el contenedor (`docker compose exec api alembic upgrade head`).
  Una prueba falla si la cadena se parte en dos (dos migraciones creadas en paralelo); se arregla con
  `alembic merge heads`.

### 2.12 Contrato de la API con los nombres del frontend
- **Decisión (25/10/2026):** las rutas y el JSON de la API están en inglés con los nombres que ya usa el frontend
  (`/api/products`, `sku`, `salePrice`…), y el backend los traduce a las columnas en español de la base. El contrato
  vive en [`API.md`](API.md) y se actualiza **antes** de programar un endpoint.
- **Por qué:** los servicios del frontend ya están hechos para cambiar `simulateRequest(...)` por llamadas reales
  sin tocar los componentes; así ese cambio es mínimo.
- Un recurso de otra empresa responde `404` (no `403`): no se revela que existe.
- No hay `DELETE` de productos: con ventas o movimientos asociados, borrar rompería el historial; se desactivan.

### 2.13 Errores con un formato único
- **Decisión (25/10/2026):** todo error responde `{"error": {"code", "message", "details"}}` (`app/core/errors.py`).
  `code` es fijo para el programa, `message` está en español para mostrarlo y `details` lista los campos inválidos.
- **Por qué:** el frontend maneja todos los errores igual, sin casos especiales por endpoint.
- Los servicios lanzan `NotFoundError`, `ConflictError`, etc., y un manejador los convierte en la respuesta. Los
  errores inesperados responden `500` sin detalles internos (quedan en los registros del servidor); si la base no
  responde, `503`.

### 2.14 Empresa de la petición: provisional por encabezado
- **Decisión (25/10/2026):** mientras no exista el login, la dependencia `get_empresa_id` (`app/api/deps.py`) toma la
  empresa del encabezado `X-Empresa-Id`, **solo con `APP_ENV=development`**; en cualquier otro entorno responde 401.
- **Por qué:** permite construir y probar los módulos con el aislamiento por empresa real, sin esperar a Supabase, y
  es imposible que quede abierto en el servidor. Con Supabase Auth solo cambia el interior de esa función.
- Los repositorios reciben la empresa al crearse (`ProductoRepository(db, empresa_id)`) y todas sus consultas la
  filtran: no existe un método que consulte sin empresa.
- **Cambio (27/10/2026): la empresa y el rol salen del token.** `get_contexto` verifica el token de Supabase y busca
  al usuario en `usuario_empresa` (solo `ACTIVO`); sin empresa asignada o inactivo: `403 NO_COMPANY`. **El token
  manda**: con token, `X-Empresa-Id` se ignora (hay una prueba que lo comprueba). El encabezado solo se acepta
  **sin token y con `APP_ENV=development`**, con rol Administrador, para probar sin login.
- La búsqueda en `usuario_empresa` es la única consulta que no filtra por `id_empresa`, porque es la que la averigua;
  busca por el id del usuario que viene verificado en el token, así que nadie puede pedir la de otro.
- **Roles:** `SoloAdministrador` (`requiere_administrador`) bloquea con `403 FORBIDDEN` lo exclusivo del
  Administrador (regla del dashboard en `CLAUDE.md`). Los roles mínimos son Administrador y Operativo (RF-1.2).
- **Modelo listo para la migración:** `app/models/usuario_empresa.py` sigue el diseño acordado (decisión 2.3):
  `id_usuario UUID` (PK, el usuario de Supabase), `id_empresa`, `id_rol`, `nombre` y `estado` (por defecto
  `ACTIVO`). Si el esquema corregido cambia algo, se ajusta el modelo.
- **Cambio (31/10/2026, Ariana): un usuario puede pertenecer a varias empresas.** `usuario_empresa` tiene clave
  primaria `(id_usuario, id_empresa)`, `id_usuario` apunta a `auth.users`, `estado` admite `ACTIVO`, `INACTIVO` e
  `INVITADO`, y el nombre pasó a `nombre_visible`. **Por qué:** por ejemplo, un contador que lleva varias PyMEs.
  - Con token: si el usuario tiene **una** empresa activa, se usa esa; si tiene **varias**, debe enviar
    `X-Empresa-Id` y el backend comprueba que pertenezca a ella (`403 COMPANY_ACCESS_DENIED` si no); sin elegir,
    `409 COMPANY_SELECTION_REQUIRED`. Esto **reemplaza** la regla anterior de que el token ignoraba el encabezado:
    ahora el encabezado elige, pero solo entre las empresas del usuario, así que sigue siendo seguro.
  - `GET /api/me/companies` (03/11/2026) lista las empresas activas del usuario sin exigir que haya elegido
    una, para que el frontend muestre el selector.
  - `gasto`, `venta` y `accion_ia` apuntan a `(id_usuario, id_empresa)` en `usuario_empresa`: la base impide
    registrar algo con un usuario de otra empresa.

### 2.15 El stock no se edita en el producto
- **Decisión (25/10/2026):** `currentStock` se fija al crear el producto; después solo cambia por ventas, compras y
  ajustes de inventario. `PATCH /api/products/{id}` lo rechaza.
- **Por qué:** cada cambio de stock debe quedar en el historial de movimientos (RF-4.3, RF-4.7); si se pudiera
  editar libremente, el historial no cuadraría con el stock.

### 2.16 Validación de la identificación del comprador (SRI)
- **Decisión (25/10/2026):** `app/sri/identificacion.py` valida según el tipo del SRI: `04` RUC, `05` cédula,
  `06` pasaporte, `07` consumidor final (solo `9999999999999`, 13 nueves) y `08` identificación del exterior.
- La **cédula** y el **RUC de persona natural** se validan de forma estricta (provincia, tercer dígito y dígito
  verificador módulo 10).
- En el **RUC de sociedades** (tercer dígito 9) y **entidades públicas** (6) se valida estricta la estructura (largo,
  provincia, tipo y establecimiento), pero si el dígito verificador módulo 11 no cuadra **se acepta con una
  advertencia**.
- **Por qué:** se ha reportado que el SRI emitió RUC de sociedades que no cumplen el algoritmo clásico; rechazarlos
  impediría facturarle a un cliente real. La advertencia permite pedir que confirme el número.

### 2.17 Clave de acceso de los comprobantes
- **Decisión (25/10/2026):** `app/sri/clave_acceso.py` arma la clave de 49 dígitos (fecha, tipo, RUC, ambiente,
  serie, secuencial, código numérico, tipo de emisión y dígito verificador módulo 11) y la valida al leerla.
- El código numérico de 8 dígitos se genera con `secrets` (al azar y no predecible), salvo que se indique uno.
- La fecha de emisión es la del calendario de Ecuador (`America/Guayaquil`), no la del servidor (UTC): una factura
  emitida a las 23:00 en Ecuador ya sería del día siguiente en UTC.

### 2.18 Totales e IVA de la factura
- **Decisión (25/10/2026):** `app/sri/totales.py` calcula los totales con `Decimal` (nunca `float`) y redondeo
  comercial `ROUND_HALF_UP` a 2 decimales (`2.665 → 2.67`; el redondeo por defecto de `Decimal` daría `2.66`).
- Por línea: `subtotal = cantidad × precio unitario − descuento`, redondeado. Cantidad y precio admiten hasta 6
  decimales (ficha técnica del SRI).
- **El IVA de cada tarifa se calcula sobre la suma de sus bases**, no sumando el IVA redondeado de cada línea.
  **Por qué:** con muchas líneas los centavos redondeados se acumulan (tres líneas de 0,10 darían 0,06 de IVA en
  vez de 0,05).
- Tarifas con su código del SRI: 15 % (`4`, general desde abril de 2024), 5 % (`5`), 0 % (`0`), no objeto (`6`) y
  exento (`7`).
- **Pendiente de confirmar** en el ambiente de pruebas del SRI (requiere el `.p12`): la tolerancia con que el SRI
  compara el IVA de las líneas contra el total por tarifa.

### 2.19 XML de la factura y esquema oficial del SRI
- **Esquema:** `backend/app/sri/xsd/factura_V2.1.0.xsd`, copiado sin cambios del archivo oficial
  "XML y XSD Factura.zip" (sección Facturación Electrónica de sri.gob.ec, descargado el 25/10/2026; 24 515 bytes,
  SHA-256 del ZIP `ba1ff0c4…26fec03`, del XSD `5f2c37bc…bd4eace`). Es la versión más reciente del comprobante.
- El esquema importa `xmldsig-core-schema.xsd` (firma XML del W3C), que no viene en el ZIP. Se usa un **reemplazo
  mínimo** que acepta `ds:Signature` con cualquier contenido. **Por qué:** permite validar facturas sin firmar sin
  descargar el esquema del W3C, que a su vez pide otros archivos por internet. La validación nunca accede a la red
  (`no_network=True`). No valida el contenido de la firma.
- `app/sri/factura_xml.py` genera el XML con `lxml` en el orden exacto del esquema, a partir de las piezas ya hechas
  (identificación, clave de acceso y totales), y exige que los pagos sumen exactamente el total.
- **Siempre valida el resultado contra el esquema** antes de devolverlo: nunca sale un XML que el SRI rechace por
  estructura.
- Formas de pago del frontend → SRI: efectivo `01`, tarjeta de débito `16`, tarjeta de crédito `19`,
  transferencia `20`.
- **Consecuencia:** el `sku` de los productos se limitó a 25 caracteres en la API (`codigoPrincipal` del XML admite
  25; la columna de la base, 50).
- Falta: firma XAdES-BES con el `.p12`, y envío y autorización en el SRI.

### 2.20 RIDE (PDF de la factura)
- **Decisión (25/10/2026):** `app/sri/ride.py` genera el RIDE con **ReportLab** **leyendo el XML de la factura**, no
  desde los datos originales.
- **Por qué leer el XML:** el PDF muestra exactamente lo que se envió al SRI; no puede haber diferencias entre ambos.
- **Por qué ReportLab:** no necesita librerías del sistema y trae el código de barras Code 128 (el de la clave de
  acceso). Se descartó WeasyPrint (HTML → PDF) porque exige Pango/Cairo en la imagen Docker.
- Todo texto que viene del usuario se **escapa** antes de dibujarse: ReportLab interpreta etiquetas tipo HTML y un
  nombre como `Pérez & Hijos <S.A.>` rompería el PDF o permitiría inyectar formato.
- Sin autorización del SRI, el RIDE dice "PENDIENTE DE AUTORIZACIÓN"; con ella, muestra el número (en el esquema
  *offline* es la misma clave de acceso) y la fecha y hora de autorización.
- Devuelve los bytes del PDF; se guarda en el almacenamiento S3 (los contenedores no guardan archivos, decisión 1.4).

### 2.21 Cliente de los servicios web del SRI
- **Decisión (25/10/2026):** `app/sri/servicios_web.py` habla con los servicios SOAP del esquema offline:
  **recepción** (`validarComprobante`, el XML firmado en base64) y **autorización** (`autorizacionComprobante`,
  con la clave de acceso). Servidores: `celcer.sri.gob.ec` (pruebas) y `cel.sri.gob.ec` (producción).
- Sin librería SOAP (`zeep`): son dos operaciones con mensajes fijos; se arman y leen con `lxml`. El HTTP usa
  `httpx2` (la misma que ya usa FastAPI para las pruebas), que pasó a ser dependencia de producción.
- Tiempo de espera de 10 s para conectar y 30 s para responder. Si el SRI no responde, responde con error 5xx o con
  algo inesperado, se lanza `SriNoDisponibleError`: el worker reintentará más tarde (decisión 2.6).
- El mensaje **43** ("clave de acceso registrada") en una recepción DEVUELTA significa que el SRI ya tenía el
  comprobante (un envío anterior que se cortó): se pasa directo a consultar la autorización.
- Si hay varias autorizaciones para una clave (intentos anteriores), vale la AUTORIZADA. Sin ninguna, el estado es
  EN PROCESO.
- **Seguridad:** las respuestas se leen con `no_network=True` y `resolve_entities=False` para bloquear ataques XXE;
  hay una prueba que lo comprueba.
- **Pendiente:** las respuestas de las pruebas son simuladas según la ficha técnica; hay que confirmarlas contra el
  ambiente de pruebas real cuando exista el `.p12`.

### 2.22 Flujo de emisión y firma intercambiable
- **Decisión (27/10/2026):** `app/sri/emision.py` (`ServicioEmision`) une las piezas: generar XML → firmar →
  enviar → consultar autorización → RIDE. El cliente del SRI, el firmador y la pausa se **reciben desde fuera**
  (inyección de dependencias): el mismo código corre en producción y en las pruebas.
- Resultados y su estado en el frontend: `autorizada` (con el RIDE), `rechazada` (DEVUELTA o NO AUTORIZADO, con los
  motivos del SRI), `por_enviar` y `por_autorizar` (ambos se muestran como "procesando").
- Tres entradas para que el worker retome una factura a medio camino: `emitir()` (desde cero), `enviar()` (las
  que quedaron por enviar; es seguro repetirlo gracias al mensaje 43) y `consultar()` (las que quedaron por autorizar).
- Espera 3 s entre el envío y la consulta, y consulta hasta 3 veces; si no hay respuesta, queda `por_autorizar` y
  el usuario no se queda esperando.
- **Firma:** `app/sri/firma.py` define `Firmador` (`firmar(xml) -> xml firmado`). Mientras no exista el `.p12`, solo
  hay `FirmadorSinFirma`, que **no firma** y **se niega a procesar comprobantes del ambiente de producción**.
  La firma XAdES-BES real es otro `Firmador` (decisión 2.23), sin tocar el flujo.

### 2.23 Firma XAdES-BES
- **Decisión (27/10/2026):** `app/sri/xades.py` (`FirmadorXadesBes`) firma como exige la ficha técnica del SRI:
  XAdES-BES 1.3.2 envuelta al final de `<factura id="comprobante">`, **RSA-SHA1**, resúmenes **SHA-1** y C14N
  inclusiva, con tres referencias firmadas (propiedades firmadas, certificado y comprobante). Las propiedades
  firmadas llevan la hora de firma en `America/Guayaquil` y la huella, emisor y número de serie del certificado.
- **SHA-1** hoy se considera débil, pero **lo exige el SRI**; con SHA-256 rechaza el comprobante. Solo se usa aquí.
- **Sin `python-xmlsec`:** implementada con `lxml` y `cryptography`, que ya están en el proyecto. Así no hacen falta
  librerías del sistema ni compilar nada en la imagen Docker.
- Antes de firmar valida que el certificado no esté vencido, que exista `id="comprobante"` y que no esté ya firmado.
- **Verificación independiente:** las pruebas verifican con `xmlsig` (solo desarrollo). Se descartó `signxml` 5.x
  porque ya no admite SHA-1. Además, la firma RSA se comprueba directamente con `cryptography`.
- **Pendiente:** confirmar que el SRI de pruebas acepta la firma con un `.p12` real. Las pruebas usan certificados
  autofirmados (`tests/certificados.py`).

### 2.24 Clientes
- **Decisión (03/11/2026):** el tipo de identificación se guarda con su código del SRI (`05` cédula, `04` RUC,
  `06` pasaporte, `08` exterior) y en la API se usa el nombre (`cedula`, `ruc`, …). Si no se envía, se deduce:
  10 dígitos = cédula, 13 = RUC; pasaporte y exterior deben indicarse.
- **Por qué:** el frontend tiene un solo campo "Cédula o RUC" en la venta, y el código del SRI es el que va en el
  XML de la factura.
- La identificación se valida con `app/sri/identificacion.py` (decisión 2.16): un RUC de sociedad con el dígito
  verificador distinto se acepta y la respuesta trae `identificationWarning`.
- El **consumidor final** (`9999999999999`) no se guarda como cliente: se usa directamente en la venta.
- Identificación única por empresa: la valida el servicio y la exige la base (si dos peticiones chocan, `409`).
- `GET /api/customers/lookup` busca por identificación exacta para autocompletar en "Nueva venta".
- La búsqueda por texto (escapando `%` y `_`) se comparte entre repositorios (`app/repositories/comun.py`).

### 2.25 Ventas
- **Decisión (03/11/2026):** el **precio y el IVA los pone el backend** desde el producto (`precio_venta`,
  `aplica_iva`); el frontend solo envía productos y cantidades. **Por qué:** si el precio viniera del navegador,
  cualquiera podría registrar una venta a $0,01.
- Los totales se calculan con `app/sri/totales.py` (decisión 2.18): la venta y su factura cuadran al centavo.
- Registrar es **una transacción**: venta, líneas, descuento de stock y movimiento de inventario `VENTA`; si algo
  falla (por ejemplo, stock insuficiente: `409 INSUFFICIENT_STOCK`), no se guarda nada.
- **Stock bajo concurrencia** (pendiente 7 de `SEGURIDAD_BD.md`): los productos se bloquean con
  `SELECT … FOR UPDATE`, ordenados por id para evitar *deadlocks*, y se valida el stock con la fila bloqueada.
  La restricción `stock_actual >= 0` de la base es la última protección.
- Registrar exige **sesión de usuario** (`venta.id_usuario` es obligatorio); el encabezado de desarrollo solo
  sirve para consultar (`403 USER_SESSION_REQUIRED`).
- Métodos de pago: `efectivo`, `tarjeta_debito`, `tarjeta_credito` y `transferencia` (la tarjeta se separa porque
  el SRI distingue débito y crédito). `tipo_origen` es `MANUAL` por ahora.
- Solo se venden productos activos de tipo `venta` o `ambos`. Las líneas de concepto libre esperan la columna de
  tarifa de IVA en `detalle_venta`.

### 2.26 Gastos
- **Decisión (20/11/2026):** las 7 categorías de RF-3.5 se **crean solas** la primera vez que la empresa las pide
  (`origen = PREDEFINIDA`); las del usuario quedan con `origen = USUARIO`. No hace falta un script por empresa.
- El RUC o la cédula del proveedor se validan con `app/sri/identificacion.py`, igual que los clientes.
- Registrar o editar un gasto exige **sesión de usuario** (`gasto.id_usuario` es obligatorio). El monto debe ser
  mayor a 0. **Pendiente con Ariana:** `gasto` no tiene columna de IVA (el frontend envía `ivaAmount`).

### 2.27 Inventario: tipos de movimiento y stock resultante
- **Decisión (20/11/2026):** `movimiento_inventario.cantidad` siempre es positiva (restricción de la base); el
  **tipo dice la dirección**: `ENTRADA` y `AJUSTE_ENTRADA` suman; `SALIDA`, `VENTA` y `AJUSTE_SALIDA` restan.
  En la API la cantidad sale con signo y los dos ajustes se muestran como `ajuste`.
- El **stock resultante** de cada movimiento no se guarda: se calcula con una función de ventana de PostgreSQL,
  hacia atrás desde el stock actual. **Por qué:** no hace falta otra columna ni que el stock inicial del
  producto se haya registrado como movimiento.
- El ajuste recibe el **stock contado**, no la diferencia, y es **solo del Administrador** (RF-4.8). Las entradas
  y salidas manuales las puede hacer cualquier usuario con sesión. Todo bloquea el producto con
  `SELECT … FOR UPDATE`, igual que las ventas.

### 2.28 Usuario demo y datos demo (solo desarrollo)
- **Decisión (20/11/2026):** con `APP_ENV=development`, el encabezado `X-Usuario-Id` (junto con `X-Empresa-Id`)
  actúa como ese usuario **usando su pertenencia real** en `usuario_empresa`: mismo rol y nombre, así los permisos
  de Administrador y Operativo se respetan. En cualquier otro entorno se ignora y se responde `401`.
- **Por qué:** registrar ventas, gastos y movimientos exige un usuario, y sin Supabase configurado no había forma
  de probarlo en Swagger ni de presentar el sistema.
- `scripts/cargar_datos_demo.py` carga una cafetería demo (productos, clientes, proveedores, gastos, ventas de 30
  días y movimientos) **pasando por la API**, con las mismas reglas que producción. Solo acepta la base local
  `iondu` y no se repite si ya hay productos.

### 2.29 Dashboard calculado en vivo
- **Decisión (20/11/2026):** `GET /api/dashboard` calcula los indicadores **en cada consulta** con `SUM`/`GROUP BY`
  en PostgreSQL, sin usar la tabla `dashboard_financiero`.
- **Por qué:** RF-5.4 pide que se actualice al confirmar cada operación; con una tabla de resumen habría que
  recalcularla en cada venta, gasto y ajuste, y podría quedar desfasada. Para el volumen de una PyME la consulta
  es inmediata. `dashboard_financiero` queda para guardar cierres mensuales si luego se necesitan.
- Los ingresos son las ventas completadas **con IVA**; los días se agrupan en hora de Ecuador.

### 2.30 Gestión de usuarios por empresa
- **Decisión (25/11/2026):** el Administrador gestiona los usuarios de **su** empresa desde Configuración > Usuarios
  (`/api/users`): crear, editar nombre y rol, activar o desactivar y restablecer la contraseña. Cada usuario cambia la
  suya en Preferencias (`POST /api/me/password`).
- **Sin correo, contraseña temporal:** como todavía no se envían correos, al crear o restablecer se genera una
  contraseña aleatoria de 16 caracteres que se muestra **una sola vez** al Administrador para que la entregue por un
  canal privado. Cuando haya correo, se cambia por un enlace de invitación.
- **Una cuenta, varias empresas:** el correo identifica a la persona. Si ya tiene cuenta por otra empresa, solo se le
  agrega la pertenencia y conserva su contraseña. Desactivar quita el acceso a esta empresa, no a la cuenta.
- **Protecciones:** nadie cambia su propio rol ni se desactiva; la empresa nunca se queda sin un Administrador activo;
  y solo se restablece la contraseña de quien trabaja **únicamente** en esta empresa (si no, el Administrador de una
  empresa podría tomar la cuenta con la que alguien entra a otra).
- **RLS (migración `f7a2d4c8e915`):** políticas nuevas en `usuario_empresa` para que el Administrador vea, agregue y
  modifique solo las pertenencias de la empresa seleccionada. La comprobación "es Administrador de esta empresa" está en
  la función `SECURITY DEFINER` `app_es_admin_de`, porque una política sobre `usuario_empresa` no puede consultar la
  misma tabla (recursión infinita). `app_usuario_en_otras_empresas` responde si alguien trabaja en otra empresa sin
  revelar cuál. `iondu_app` puede insertar en `usuario` solo `id`, `email` y `password_hash`.
- **Verificado con el rol real:** se probó la API conectada como `iondu_app` (sin privilegios) contra una base con
  todas las migraciones; las pruebas automáticas corren como dueño de las tablas y no ejercitan el RLS.

### 2.31 Auditoría escrita por el backend
- **Decisión (26/11/2026):** la auditoría la escribe la API al terminar bien cada acción (dependencia `AuditorActual`
  en los endpoints) y solo el Administrador la consulta (`GET /api/audit`). Antes el frontend la simulaba con
  `audit.log()`, que cualquier cliente podía omitir o falsificar; esas llamadas se eliminaron.
- **Solo inserción:** `iondu_app` tiene INSERT y SELECT sobre `auditoria`, sin UPDATE ni DELETE. RLS: cada usuario
  registra en su empresa y a su nombre; solo el Administrador lee.
- **Transacción aparte:** se registra después de que la acción se guardó. Si el registro fallara, la acción del
  usuario no se deshace y el fallo queda en el log del servidor (`iondu.auditoria`), no se oculta.
- **INSERT explícito sin RETURNING:** un Operativo puede insertar pero no leer la auditoría, y con `RETURNING`
  PostgreSQL exige también la política de lectura. El INSERT del ORM agrega `RETURNING` (o `nextval()` si se le
  quita), así que se usa SQL explícito (ver "Trampas técnicas"). Se detectó probando con el rol real: las pruebas
  automáticas no ejercitan el RLS.
- **Pendiente:** registrar inicios de sesión y las propuestas confirmadas del agente de IA cuando exista (módulos
  `auth` e `ia`).

### 2.32 Agente de IA: el modelo propone, el backend decide
- **Decisión (26/11/2026):** cliente único compatible con la API de OpenAI (`/v1/chat/completions`). En local se usa
  **Ollama** con `qwen2.5:7b` en la GPU (gratis, sin clave, los datos no salen de la computadora); en producción, la URL,
  el modelo y la clave del proveedor externo que pide RF-6.1 (variables `LLM_*`). El VPS previsto (2 vCPU, 4 GB, sin GPU)
  no puede correr un modelo útil.
- **El modelo solo propone.** Responde con salida estructurada (JSON Schema) y el backend la valida con reglas en código:
  acciones permitidas (`registrar_gasto`, `movimiento_inventario`, `pedir_aclaracion`, `fuera_de_alcance`), montos entre $0,01 y $1.000.000, IVA
  no mayor que el total, categoría existente, método de pago válido y fecha de hasta un año atrás. Lo que no cumple se
  trata como "no entendí".
- **Nunca toca ingresos (RF-6.7):** no existe ningún camino de código del agente a ventas o facturas; no depende del
  prompt. Las instrucciones escondidas en el mensaje ("ignora tus reglas…") se rechazan igual.
- **La propuesta vive en el servidor** (`accion_ia`, estado PENDIENTE) y al confirmar se ejecuta esa misma propuesta, con
  las correcciones permitidas, por `GastoService`. El cambio de estado y el gasto van en la misma transacción con la
  fila bloqueada: no se puede confirmar dos veces. Queda en la auditoría con el módulo `ia`.
- **Tokens:** cada llamada guarda su consumo en `consumo_tokens` (RF-6.14); los límites por empresa (RNF-12) llegan después.
- **Probado con el modelo real:** 7 de 7 categorías correctas en casos típicos, respuestas en 2 a 9 s, ventas e intentos
  de manipulación rechazados. Un modelo de 7B se equivoca más que uno grande: la confirmación humana es obligatoria.
- **Inventario (etapa 2):** el modelo elige el producto de una lista cerrada (los activos de la empresa, con su código
  para distinguir homónimos) más la opción "otro producto". Como un modelo pequeño tiende a elegir uno parecido aunque
  el usuario hable de otro, el código exige que el mensaje **mencione** el producto (una palabra clave con sus primeras
  4 letras: "croissants" ↔ "Croissant"); si no, pregunta. Una salida no puede superar el stock y los ajustes por conteo
  solo los propone y confirma un Administrador (RF-4.8). Si el modelo corta el JSON, se reintenta una vez.
- **Pendiente:** una compra con precio ("compré 10 croissants por $8") hoy propone solo el gasto; proponer gasto y
  entrada de inventario juntos (RF-6.8) queda para después.
- **Imagen (etapa 3, RF-6.3):** `POST /api/ai/images` con un modelo de visión aparte (`LLM_VISION_MODEL`; en local
  `qwen2.5vl:7b`, unos 6 GB, que Ollama alterna en la GPU con el de texto). La foto se valida con Pillow (formato real,
  tope de píxeles contra "bombas" de descompresión), se gira según el EXIF, se le quitan los metadatos (GPS) y se reduce
  a 1280 px; se procesa en memoria y **no se guarda** (contenedores sin estado): en `accion_ia` queda solo lo que el
  modelo leyó (`lectura`, máx. 400 caracteres). El prompt agrega reglas de comprobantes: el total a pagar, el IVA, el
  emisor como proveedor y la fecha de emisión; una guía de remisión es una entrada de inventario; una factura emitida
  por la propia empresa (se le da su razón social y RUC) es una venta y se rechaza. Tres correcciones en código, vistas
  con el modelo real: el **método de pago** sale de lo leído cuando dice uno solo ("Tarjeta de crédito"), porque el
  modelo lo transcribía bien pero elegía débito; el producto debe **aparecer en lo leído** o en la indicación (misma
  regla que en texto); y si el modelo clasifica la foto como `otra_cosa`, el mensaje lo pone el código (el modelo decía
  "no puedo interpretar imágenes"). Un sí/no (`es_comprobante`) fallaba más que tres opciones descriptivas.
- **Reintento distinto:** con temperatura 0 un reintento repite la misma respuesta. El modelo de visión entró en bucle
  ("#IONDU #IONDU…" hasta agotar los tokens) con una factura de venta; el reintento usa temperatura 0,4 y penalización
  por repetición, y lo resolvió. Los tokens de los dos intentos se suman en `consumo_tokens`.
- **Probado con el modelo real (etapa 3):** factura de compra (total, IVA, proveedor, fecha, Empaque, tarjeta de
  crédito), ticket de gasolinera (Transporte, efectivo), guía de remisión (entrada de 24 croissants), factura emitida
  por la empresa (rechazada como venta) y una foto sin comprobante (pide otra). De 5 a 25 s por foto; la primera tarda
  más porque Ollama carga el modelo.
- **Voz (etapa 4, RF-6.4):** `POST /api/ai/audio`. El audio se transcribe con la API de OpenAI
  (`/v1/audio/transcriptions`, variables `STT_*`) y luego sigue exactamente el camino del texto: mismas reglas, mismo
  modelo. En local, el servicio `stt` (speaches con Whisper `faster-whisper-small`, en CPU para no competir con Ollama
  por la GPU) solo se levanta con `COMPOSE_PROFILES=ia`; al arrancar descarga el modelo (~500 MB) si no está en el
  volumen, porque esta versión de speaches ya no lo precarga. En producción basta con apuntar `STT_BASE_URL` a un
  proveedor (p. ej. OpenAI con `whisper-1`). El formato se valida por sus primeros bytes (no por el nombre) y el audio
  no se guarda: en `accion_ia` queda la transcripción. La respuesta incluye `transcript` y el chat la muestra en la
  burbuja del usuario, para que se vea qué se entendió antes de confirmar. El navegador graba con `MediaRecorder`
  (WebM/Opus en Chrome, MP4 en Safari), hasta un minuto.
- **Probado con el modelo real (etapa 4):** con voces sintéticas de Kokoro, las cuatro frases se transcribieron
  palabra por palabra y dieron la propuesta correcta (gasto de empaque, entrada de croissants, luz por transferencia) o
  el rechazo de la venta; de 8 a 19 s por mensaje. Una voz sintética de peor calidad (Piper) se transcribía mal
  ("Gasté" → "Verás") también con el modelo `medium`: el problema era la voz, no el tamaño del modelo, así que se dejó
  `small` (unos 5 s por mensaje en CPU frente a unos 14 s de `medium`). Falta probarlo con voces reales y con ruido.
- **Etapas:** 1) texto y gastos ✅; 2) inventario ✅; 3) imagen ✅; 4) voz ✅; 5) límites de tokens.

## 3. Producto

### 3.1 Ventas y Facturación son un solo módulo
- **Decisión:** al registrar una venta hay un interruptor **"Emitir factura electrónica", activado por defecto** en
  cada venta nueva. El historial de ventas muestra el estado de la factura (Autorizada, En proceso, Rechazada,
  Sin factura) y permite emitirla después o reintentar una rechazada corrigiendo la cédula o el RUC.
- **Por qué:** los requisitos dicen que cada factura autorizada se registra automáticamente como venta; tener dos
  módulos obligaba a elegir a mano la venta a facturar.
- La factura se emite **en segundo plano**: la venta se registra y el usuario pasa al historial, donde el estado
  cambia en vivo. Las rutas antiguas `/billing/*` redirigen a `/sales/history`.
- La validación de negocio de la factura (por ejemplo, los límites del SRI para consumidor final) se hará en el backend.

### 3.1.1 Inventario sin recetas ni fabricación (17 de octubre de 2026)
- **Decisión:** se retiran del producto las recetas, la fabricación y el tipo "producto compuesto". Los tipos son
  solo **Producto** e **Insumo**. Las rutas `/inventory/recipes` y `/inventory/production` redirigen a Productos.
- **Por qué:** los clientes indicaron que no pueden calcular la merma y que no usarán esa función.
- **Consecuencia:** los movimientos de stock son entrada, salida, ajuste y venta. Si en el futuro se retoma, hay que
  volver a diseñarlo desde cero; el código anterior solo queda en el historial de git.

### 3.1.2 Alta de productos: código y categoría automáticos, carga masiva
- **Código:** opcional. Si se deja vacío se genera `PS-###` (producto) o `IN-###` (insumo), siguiendo el último número usado.
- **Categoría y unidad:** campo de texto con sugerencias (las ya usadas más algunas comunes); se puede escribir una nueva.
- **Carga masiva:** "+ Nuevo producto" pregunta si es individual o desde un documento. El documento puede ser **CSV** o
  **Excel (.xlsx)**; hay plantilla descargable con las columnas en orden (Código, Nombre*, Categoría*, Tipo, Unidad,
  Precio de venta, Costo, Stock actual, Stock mínimo). Se valida fila por fila, se muestra una vista previa y solo se
  importan las filas válidas (máximo 1000 filas y 2 MB). El CSV acepta coma o punto y coma, y decimales con coma.
- **Librerías:** `read-excel-file` y `write-excel-file` (versión `universal`, sin Web Workers), cargadas solo al usar la carga masiva.
- **Pendiente con el backend:** hoy las filas se crean en memoria (*mock*); cuando exista la API, la importación debe
  hacerse en una sola petición transaccional, filtrada por `id_empresa`.

### 3.2 Tema claro y oscuro
- **Decisión:** el tema por defecto **sigue al sistema**; hay un botón en la cabecera para alternar
  (sistema → claro → oscuro).

### 3.3 Cierre de sesión
- **Decisión:** al cerrar sesión se borran `localStorage`, `sessionStorage` y la caché del service worker.
- **Por qué:** las PyMEs comparten computadoras; no deben quedar datos de una empresa para la siguiente persona.
- **Consecuencia aceptada:** también se pierden el tema y el ancho del menú. Si se prefiere conservarlos, es un cambio pequeño.

## 4. Diseño y frontend

### 4.1 Identidad visual
- **Colores:** blanco, negro y **un solo acento morado**. Sin degradados azul-morado (el skill de diseño los marca
  como el cliché de las interfaces generadas). Los neutros llevan un matiz violeta leve; las sombras son del mismo matiz.
- **Tokens** en `frontend/src/styles/_tokens.scss`; todo el color sale de ahí. Cada color de texto sobre fondo
  de marca tiene su par (`--color-on-primary`, `--color-on-danger`) para cumplir el contraste.
- **Fuente: Geist** (variable), incluida con la app vía npm, no desde Google: la PWA funciona sin conexión y no se
  envían datos a terceros. Cifras tabulares para que los montos se alineen.
- **Íconos: Phosphor**, generados como un registro propio (`npm run icons`) para no cargar la librería completa
  ni depender de una versión de Angular. Reemplazan a los 89 emojis. Se descartó Lucide (sin compatibilidad
  declarada con Angular 22) y se evitó el uso exclusivo de las librerías más genéricas.
- **Logo:** vectorizado a SVG con `currentColor` para que cambie solo entre tema claro y oscuro. Se hizo a partir de
  un PNG borroso; **conviene sustituirlo por el SVG original** del diseño (`shared/components/logo/logo-mark.const.ts`).

### 4.1.1 Ventanas flotantes (modal)
- Solo se cierran con un clic que **empieza y termina** sobre el fondo. Si se presiona dentro del cuadro y se suelta
  afuera (por ejemplo, al seleccionar texto), no se cierra.

### 4.2 Menú lateral
- Retráctil a una columna de íconos, **redimensionable** (arrastrando el borde o con el teclado, 220–360 px),
  con **varios grupos abiertos a la vez** y recordando su estado.
- En cada grupo, la **primera opción es la pantalla a la que redirige** el título.
- En móvil es un cajón; cerrado es inerte (no recibe foco) y Escape lo cierra.

### 4.3 Dashboard
- Dos filas con las mismas columnas (2/3 y 1/3) para que los bordes queden alineados; tarjetas de igual altura.
- Los componentes responden al **ancho real disponible** (container queries), no al de la ventana, porque el menú
  cambia el espacio.
- Los datos de ejemplo son **relativos a la fecha actual** y determinísticos, así el dashboard nunca sale vacío.

### 4.4 Transición entre páginas
- **Decisión:** la página anterior **desaparece al instante** y la nueva se desvanece con un leve ascenso (260 ms)
  sobre un lienzo vacío; así nunca conviven las dos. Usa la View Transitions API del navegador; sin soporte,
  el cambio es inmediato. Respeta "reducir movimiento".
- El nombre de la transición se aplica **solo mientras dura**: de forma permanente crea un contexto de apilamiento
  que deja los modales por debajo de la cabecera.

### 4.5 Tablas y móvil
- En pantallas pequeñas las tablas se muestran como **tarjetas** con pares etiqueta-valor, sin desplazamiento lateral.
- Las filas clicables se operan con teclado. Probado sin desborde a 320, 390 y 768 px.

### 4.6 Accesibilidad (meta: 100 en Lighthouse)
- Etiquetas vinculadas a sus campos (`FormField`), modales con foco atrapado y devuelto, orden correcto de encabezados,
  contraste suficiente en ambos temas y objetivos táctiles de al menos 24 px.
- Estado actual: 100 en las 19 pantallas auditadas en escritorio, y en las principales en móvil.

## 5. Proceso de trabajo

### 5.1 Repositorio
- Monorepo: `frontend/`, `backend/`, `docs/`. Se renombró `IONDU CODE` a `frontend` (el espacio rompía Dockerfiles
  y scripts) y `DOCS` a `docs`.

### 5.2 Commits
- Formato `tipo(alcance): descripción` en español, **sin menciones a IA** ni `Co-authored-by`, un commit por cambio
  lógico y sin mezclar renombres con cambios de contenido. Detalle en `CLAUDE.md`.
- Antes de commitear se revisa que no entre `.env`, `*.p12`, `*.pfx` ni `*.zip`.

### 5.3 Herramientas de diseño y revisión
- Se instalaron los plugins `taste-skill`, `ui-ux-pro-max` e `impeccable`. Para no mezclar criterios: `ui-ux-pro-max`
  para fuentes y paleta, `taste-skill` para el estilo, `impeccable` para auditar y pulir.
- `impeccable` instala un hook que revisa los archivos de interfaz al editarlos y envía telemetría anónima
  (se desactiva con `DO_NOT_TRACK=1`). Necesita `/impeccable init` una vez.

### 5.4 Revisión de código del backend con Ruff
- **Decisión (21/10/2026):** Ruff revisa (`ruff check`) y formatea (`ruff format`) el código Python; la configuración
  está en `backend/pyproject.toml`. El CI falla si el código no pasa.
- **Por qué:** detecta errores comunes antes de ejecutar (imports o variables sin usar, código simplificable) y deja
  un solo estilo sin importar quién escribe. Se agregó con el backend chico, para no tener que corregir cientos de
  archivos después.
- Reglas: estilo PEP 8 (`E`, `W`), errores (`F`), orden de imports (`I`), errores sutiles (`B`), sintaxis moderna
  (`UP`), simplificaciones (`SIM`) y nombres (`N`). Línea máxima de 100 caracteres.
- La plantilla de migraciones se modernizó para que cumpla las reglas, y Alembic formatea cada migración nueva con
  Ruff al crearla.

### 5.5 Entorno de desarrollo del backend
- Python 3.12 (la misma versión que la imagen Docker) con un entorno virtual en `backend/.venv`, que no se sube al
  repositorio. Permite autocompletado en el editor y correr las pruebas en segundos sin construir Docker.
- Docker sigue siendo la referencia: el CI prueba dentro de la imagen.

### 5.6 Pruebas con base de datos
- **Decisión (25/10/2026):** las pruebas que necesitan PostgreSQL usan `TEST_DATABASE_URL`, en una base aparte cuyo
  nombre **debe terminar en `_test`** (las pruebas borran y crean sus tablas; con otro nombre se niegan a correr).
- Cada prueba corre dentro de una transacción que se deshace al terminar (los `commit()` del código se vuelven
  *savepoints*): las pruebas no se afectan entre sí y no dejan datos.
- Sin la variable, esas pruebas se saltan (por ejemplo, al construir la imagen). En el CI, el trabajo del backend
  levanta un PostgreSQL temporal y corre todas.

## 6. Trampas técnicas conocidas

| Situación | Qué pasa | Qué hacer |
|---|---|---|
| `INSERT ... RETURNING` bajo RLS | Si el rol puede insertar pero la política de lectura no le deja ver la fila, el INSERT falla con "new row violates row-level security policy". El ORM de SQLAlchemy agrega `RETURNING` (o `nextval()` sobre la secuencia) sin pedirlo | Insertar con SQL explícito sin `RETURNING`, como `app/services/auditoria.py` |
| Saltos de línea | Varios archivos del frontend usan CRLF (Windows); los reemplazos de texto automáticos fallan sin avisar | Normalizar a `\n` antes de reemplazar y restaurar CRLF; o agregar un `.gitattributes` |
| Pruebas del backend | Hace falta Python 3.12 para correrlas sin Docker | `docker build --target test backend`, o el entorno virtual `backend/.venv` (ver 5.5) |
| `docker compose up` falla pidiendo `POSTGRES_PASSWORD` | El override exige la contraseña de la base local | Agregar `POSTGRES_PASSWORD=<cualquier valor>` al `.env` |
| `Ports are not available` al levantar `db` | Otro PostgreSQL (o programa) ya usa el puerto | La base local usa 15432; si también está ocupado, cambiarlo en `docker-compose.override.yml` |
| Ruff quiere mover `from alembic import ...` | La carpeta `backend/alembic/` le hace creer que es código propio | Ya resuelto con `known-third-party = ["alembic"]` en `pyproject.toml` |
| Conectar desde Windows a `localhost:15432` se queda colgado | `localhost` intenta primero IPv6 (`::1`) y el contenedor solo escucha en `127.0.0.1` | Usar `127.0.0.1` en las direcciones de conexión |
| Tildes rotas al probar con `curl` en Windows | La terminal no envía el texto en UTF-8 y la API responde `400 BAD_REQUEST` | Enviar el JSON desde un archivo UTF-8 (`--data-binary @archivo.json`) o probar en `/api/docs` |
| `/api/docs` sigue mostrando un error viejo | El navegador guardó en caché una respuesta anterior | Recargar sin caché o abrir en una ventana privada |
| Docker no responde (`error during connect` o error 500) después de suspender la computadora | El motor de Docker Desktop quedó trabado aunque el programa siga abierto | `docker desktop restart` |
| Falla `test_migraciones_forman_una_sola_cadena` | Dos migraciones creadas en paralelo dejaron dos "heads" | `alembic merge heads -m "unir migraciones"` |
| Agregar un ícono | Los íconos son un registro generado | Añadirlo en `frontend/scripts/generate-icons.mjs` y correr `npm run icons` |
| Contenedor en `localhost:8080` | Usa la imagen de la última construcción | `docker compose up -d --build` |
| Modal tapado por la cabecera | Un `view-transition-name` permanente crea un contexto de apilamiento | Mantenerlo solo durante la transición (ya implementado en `app.config.ts`) |
| Rejillas de una columna | `1fr` no encoge por debajo de su contenido y desborda en móvil | Usar `minmax(0, 1fr)` y `minmax(min(Npx, 100%), 1fr)` |
| `git` avisa LF→CRLF | Aviso en cada commit | Inocuo; se resuelve con `.gitattributes` |

## 7. Decisiones abiertas

- **Proveedor y región del VPS** y **dominio**: los define el cliente. Supabase debe quedar en una región cercana.
- **Logo definitivo** en SVG por parte del diseño.
- **Conservar o no** el tema y el ancho del menú al cerrar sesión.
- **Imágenes en GHCR** construidas por GitHub Actions, en lugar de compilar Angular en el VPS (recomendado si el
  servidor del cliente es pequeño).
- **Redis/Celery** para el worker, solo si el volumen lo justifica.
- **Tipos de producto:** `simple / insumo / compuesto` (frontend) o `venta / insumo / ambos` (RF-4.1); la tabla
  `producto` hoy usa `VENTA` por defecto. Hay que elegir uno y usarlo en los tres lados.
- **Recetas y Producción:** el frontend tiene esas pantallas, pero no están en `REQUISITOS.md` ni tienen tablas.
  Confirmar con el cliente si entran en el MVP.
- **Quién crea y administra el proyecto de Supabase** del equipo.
