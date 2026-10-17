# syntax=docker/dockerfile:1.7
# ============================================================
# IONDU · Frontend Angular (PWA) → Nginx
# Etapa 1: compilación con Node | Etapa 2: servidor estático Nginx
# ============================================================

# ---------- Etapa 1: build ----------
FROM node:22-alpine AS build
WORKDIR /app

# Evita que el build se quede sin memoria en un VPS pequeño
ENV NODE_OPTIONS=--max-old-space-size=2048 \
    NG_CLI_ANALYTICS=false

# 1) Solo manifiestos primero → la capa de dependencias se cachea
COPY package.json package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci --no-audit --no-fund

# 2) Código fuente
COPY . .

# Configuración de Angular a usar (production / staging)
ARG BUILD_CONFIGURATION=production
RUN npx ng build --configuration=${BUILD_CONFIGURATION}

# ---------- Etapa 2: runtime ----------
FROM nginx:1.27-alpine AS runtime

# Nombre del proyecto en angular.json → dist/<APP_NAME>/browser (Angular 17+)
ARG APP_NAME=iondu-app

RUN rm -f /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/iondu.conf
COPY security-headers.inc /etc/nginx/conf.d/security-headers.inc

COPY --from=build /app/dist/${APP_NAME}/browser /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD wget -qO- http://127.0.0.1/healthz || exit 1
