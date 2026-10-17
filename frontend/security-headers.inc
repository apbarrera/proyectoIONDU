# Cabeceras de seguridad (se incluyen en cada location porque en Nginx
# un add_header dentro de location anula los del nivel server).
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "DENY" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
# Cámara y micrófono permitidos solo para la propia app (fotos de facturas / voz al agente IA)
add_header Permissions-Policy "camera=(self), microphone=(self), geolocation=()" always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
# CSP: activar en modo Report-Only primero y endurecer cuando no rompa nada
# add_header Content-Security-Policy-Report-Only "default-src 'self'; img-src 'self' data: blob: https:; style-src 'self' 'unsafe-inline'; connect-src 'self' https://*.supabase.co https://*.sentry.io; frame-ancestors 'none'" always;
