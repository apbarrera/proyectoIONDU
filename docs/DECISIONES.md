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
- **Decisión:** nada se guarda en el disco de los contenedores. Archivos, PDF, XML e imágenes van a Supabase Storage.
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
- **Decisión (20/10/2026):** `docker-compose.override.yml` agrega un servicio `db` con PostgreSQL 17 (la misma
  versión mayor que Supabase). Si `DATABASE_URL` está vacía en el `.env`, la API y el worker usan esta base; si
  tiene la dirección de Supabase, usan Supabase.
- **Por qué:** cada uno desarrolla y prueba sin depender de Supabase (que todavía no existe) ni de internet, y como
  Supabase es PostgreSQL, lo que funciona aquí funciona allá cambiando una variable.
- Se publica solo en `127.0.0.1:15432` (no se ve desde la red). Se eligió 15432 porque en la máquina de desarrollo
  ya había PostgreSQL instalados en 5432, 5433 y 5434.
- La contraseña no está en el repositorio: se lee de `POSTGRES_PASSWORD` en el `.env`, que es obligatoria.
- Usa un volumen (`db-data`) para no perder los datos al apagar el contenedor. Es la única excepción a la decisión
  1.4, y solo en local: Coolify no lee el override.

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

### 2.3 Autenticación: Supabase Auth
- **Decisión:** Supabase Auth para la identidad; una tabla propia `usuario_empresa (id_usuario UUID, id_empresa, id_rol, …)`
  para el tenant y los permisos.
- **Por qué:** el presupuesto ya incluía Supabase Auth, pero el diagrama de login usaba contraseñas propias con IDs
  enteros. Supabase identifica a los usuarios con UUID y guarda sus propias contraseñas; no se duplican.

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
- `env.py` lee la dirección de `DATABASE_URL` (nunca de `alembic.ini`) y **nunca propone borrar una tabla que no tenga
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
- Devuelve los bytes del PDF; se guardará en Supabase Storage (los contenedores no guardan archivos, decisión 1.4).

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
| Saltos de línea | Varios archivos del frontend usan CRLF (Windows); los reemplazos de texto automáticos fallan sin avisar | Normalizar a `\n` antes de reemplazar y restaurar CRLF; o agregar un `.gitattributes` |
| Pruebas del backend | Hace falta Python 3.12 para correrlas sin Docker | `docker build --target test backend`, o el entorno virtual `backend/.venv` (ver 5.5) |
| `docker compose up` falla pidiendo `POSTGRES_PASSWORD` | El override exige la contraseña de la base local | Agregar `POSTGRES_PASSWORD=<cualquier valor>` al `.env` |
| `Ports are not available` al levantar `db` | Otro PostgreSQL (o programa) ya usa el puerto | La base local usa 15432; si también está ocupado, cambiarlo en `docker-compose.override.yml` |
| Ruff quiere mover `from alembic import ...` | La carpeta `backend/alembic/` le hace creer que es código propio | Ya resuelto con `known-third-party = ["alembic"]` en `pyproject.toml` |
| Conectar desde Windows a `localhost:15432` se queda colgado | `localhost` intenta primero IPv6 (`::1`) y el contenedor solo escucha en `127.0.0.1` | Usar `127.0.0.1` en las direcciones de conexión |
| Tildes rotas al probar con `curl` en Windows | La terminal no envía el texto en UTF-8 y la API responde `400 BAD_REQUEST` | Enviar el JSON desde un archivo UTF-8 (`--data-binary @archivo.json`) o probar en `/api/docs` |
| `/api/docs` sigue mostrando un error viejo | El navegador guardó en caché una respuesta anterior | Recargar sin caché o abrir en una ventana privada |
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
