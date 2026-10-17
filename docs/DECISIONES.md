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
- **Decisión:** una sola imagen; el worker solo cambia el comando (`python -m app.worker`).
- **Por qué:** una compilación, las mismas dependencias y menos mantenimiento.
- La compilación incluye un *target* `test` que ejecuta `pytest`: si una prueba falla, falla la construcción.

### 1.7 Nginx y la PWA
- `ngsw-worker.js`, `ngsw.json` e `index.html` se sirven **sin caché** (si se cachean, los usuarios quedan atascados
  en versiones viejas). Los archivos con hash llevan caché de un año (`immutable`).
- El service worker exige HTTPS, que cubre Traefik. `/api/**` se excluye de la navegación del service worker.

### 1.8 Integración continua
- **GitHub Actions** en cada push y pull request: pruebas y build del frontend, pruebas del backend (en Docker)
  y construcción de las imágenes. Opcional a futuro: construir las imágenes en Actions y publicarlas en GHCR para
  que el VPS solo las descargue.

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

## 6. Trampas técnicas conocidas

| Situación | Qué pasa | Qué hacer |
|---|---|---|
| Saltos de línea | Varios archivos del frontend usan CRLF (Windows); los reemplazos de texto automáticos fallan sin avisar | Normalizar a `\n` antes de reemplazar y restaurar CRLF; o agregar un `.gitattributes` |
| Pruebas del backend | No hay Python instalado en la máquina de desarrollo | `docker build --target test backend` |
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
