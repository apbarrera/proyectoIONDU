# IONDU · Guía de despliegue con Docker

Para quien administra el servidor (el cliente). La idea es simple: **el sistema completo se levanta con un solo comando** en cualquier servidor con Docker, o desde Coolify si lo usan.

## Estado actual

Hoy solo existe el **frontend** (Angular PWA con datos de ejemplo, sin backend). El `docker-compose.yml` levanta ese único servicio, `web`. Cuando exista el backend se agregan `api` y `worker` (ver "Siguientes pasos").

## Requisitos del servidor

- Ubuntu 24.04 (u otro Linux), **2 vCPU y 4 GB de RAM** como mínimo (la compilación de Angular consume memoria; con 2 GB falla).
- Docker Engine 24+ y el plugin Docker Compose.
- Un dominio apuntando a la IP del servidor.
- Puertos abiertos: 22, 80 y 443. Nada más.

## Opción A · Docker Compose directo (con tu propio proxy HTTPS)

```bash
git clone https://github.com/apbarrera/proyectoIONDU.git
cd proyectoIONDU
cp .env.example .env          # ajustar valores si hace falta
docker compose up -d --build
```

Para probar en el propio servidor o en un PC, `docker-compose.override.yml` publica el puerto 8080: abrir `http://localhost:8080`.

**En producción hay que quitar la publicación de puertos** (usar solo `docker-compose.yml`, que usa `expose`) y poner delante un proxy inverso con HTTPS (Traefik, Caddy, Nginx Proxy Manager…) que apunte al contenedor `web`, puerto 80. Docker se salta el firewall (UFW), por eso no se publican puertos del host.

## Opción B · Coolify (recomendada)

Coolify es un panel que se instala en el VPS y se encarga del proxy HTTPS (Traefik + Let's Encrypt), los despliegues desde GitHub y las variables de entorno.

1. Instalar Coolify: `curl -fsSL https://cdn.coollabs.io/coolify/install.sh | sudo bash`.
2. Asignar un dominio al panel y cerrar el puerto 8000 del firewall.
3. **Sources → GitHub App**: dar acceso solo al repositorio de IONDU.
4. **Projects → IONDU**: crear los entornos `production` (y `staging` si se quiere).
5. **New Resource → Docker Compose**: repositorio, rama `main`, ruta `/docker-compose.yml`.
6. Asignar el dominio **solo al servicio `web`**, por ejemplo `https://app.iondu.org`. Coolify emite el certificado.
7. Cargar las variables en **Environment Variables** y desplegar.
8. Activar notificaciones de despliegues fallidos y snapshots del VPS.

Si el dominio está en Cloudflare con el proxy activado (nube naranja), usar el modo SSL **Full (strict)**; "Flexible" provoca bucles de redirección.

## Variables de entorno

Plantilla en [`.env.example`](../.env.example). **Nunca** se suben al repositorio el archivo `.env`, ni certificados `.p12`/`.pfx`; el `.gitignore` ya los excluye.

## Qué incluye la imagen del frontend

- Compila con Node 22 y sirve con Nginx Alpine (imagen final pequeña).
- Rutas de la SPA (`/ventas/123` entrega `index.html`).
- Caché correcta para la PWA: `ngsw-worker.js`, `ngsw.json` e `index.html` **sin caché**; los archivos con hash, un año.
- Reenvío de `/api/*` al contenedor `api` por la red interna (mismo origen: sin CORS).
- Cabeceras de seguridad y healthcheck en `/healthz`.

## Siguientes pasos (cuando exista el backend)

1. Agregar `backend/` con su Dockerfile (una sola imagen para la API y el worker).
2. Agregar los servicios `api` y `worker` al `docker-compose.yml` y las variables de Supabase, SRI, IA y correo al `.env.example`.
3. Crear `environment.prod.ts` con `apiUrl: '/api'` y conectar los servicios de Angular (hoy son *mock*).
4. Conectar a Supabase por el **Session Pooler** (`*.pooler.supabase.com:5432`): la conexión directa es solo IPv6 y Docker en un VPS sale normalmente por IPv4.
5. Guardar los `.p12` cifrados (AES-GCM) en la base o en Supabase Storage: así ningún contenedor necesita volúmenes.

## Comandos útiles

```bash
docker compose ps                  # estado y salud de los servicios
docker compose logs -f web         # logs en vivo
docker compose up -d --build       # actualizar tras un git pull
docker compose down                # detener todo
```
