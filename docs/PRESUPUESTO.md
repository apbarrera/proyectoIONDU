# IONDU · Presupuesto de infraestructura y servicios (corregido)

> Versión alineada con el despliegue en **Docker sobre un VPS administrado por el cliente**.
> Reemplaza a `Tabla de presupuesto.xlsx` (la versión original queda en esta carpeta como referencia).

## Qué cambió respecto a la versión original

| Fila original | Cambio | Motivo |
|---|---|---|
| 2 · Vercel Pro ($20) | **Eliminada** | El frontend se sirve desde un contenedor Nginx en el VPS del cliente. |
| 3 · DigitalOcean App Platform ($12) | **Eliminada** | La API y el worker corren como contenedores en el mismo VPS. |
| 11 · Procesos programados de DigitalOcean | **Reemplazada** | Los procesos periódicos los ejecuta el contenedor `worker`. |
| 15 · SSL (Vercel + Cloudflare) | **Reemplazada** | El certificado lo emite el proxy inverso del VPS (Let's Encrypt). |
| 16 · Secretos de DigitalOcean | **Reemplazada** | Las claves se cargan como variables de entorno del despliegue. |
| 13 · GitHub Free | **Corregida** | Decía $0 de costo pero sumaba $4 al total, sin justificación. Se deja en $0. |
| Nuevas | **Agregadas** | VPS (a cargo del cliente), Docker, registro de imágenes (GHCR) y respaldo del VPS. |

## Tabla de costos

| # | Categoría | Servicio / Tecnología | Modalidad | Costo del servicio | Costo mensual considerado | ¿Oblig.? | ¿Para qué se utiliza? |
|---|---|---|---|---|---|---|---|
| 1 | Dominio | Cloudflare — dominio .com (`iondu.org`) | Anual | $11,20 | $0,93 | Sí | Dirección web oficial. El costo corresponde al primer año. |
| 2 | Servidor (VPS) | VPS con Docker, **proporcionado y administrado por el cliente** | A cargo del cliente | $0 para el proyecto | $0,00 | Sí | Ejecutar los contenedores del frontend, la API y el worker. Mínimo recomendado: 2 vCPU y 4 GB de RAM (Ubuntu 24.04). |
| 3 | Contenedores | Docker + Docker Compose | Gratis (open source) | $0,00 | $0,00 | Sí | Empaquetar y ejecutar la aplicación de forma idéntica en desarrollo y producción. |
| 4 | Base de datos | Supabase Pro — PostgreSQL | Mensual | $25,00 | $25,00 | Sí | Usuarios, empresas, ventas, gastos, inventario, configuración y facturas. |
| 5 | Autenticación | Supabase Auth | Incluido en Supabase | $0 adicional | $0,00 | Sí | Inicio de sesión, sesiones activas y recuperación de contraseña. |
| 6 | Almacenamiento | Supabase Storage | Incluido / consumo | $0 adicional | $0,00 | Sí | Comprobantes XML, PDF, imágenes y certificados `.p12` cifrados. |
| 7 | Integración SRI | Desarrollo propio en Python | Desarrollo propio | $0 | $0,00 | Sí | Generar, firmar, enviar, autorizar y consultar comprobantes electrónicos. |
| 8 | Firma electrónica | Certificado `.p12` del cliente | Proporcionado por el cliente | $0 para el proyecto | $0,00 | Sí | Firmar los comprobantes antes de enviarlos al SRI. |
| 9 | IA multimodal | OpenAI API (GPT-4o-mini) | Por consumo | ~$15,00 | $15,00 | Sí | Texto, imágenes y voz para captura inteligente y recomendaciones. Varía según el uso. |
| 10 | Correos | Resend Pro + lectura IMAP (backend) | Mensual + desarrollo propio | $20,00 | $20,00 | Sí | Correos transaccionales y lectura automática de facturas recibidas. |
| 11 | Procesos programados | Contenedor `worker` (misma imagen que la API) | Incluido en el VPS | $0,00 | $0,00 | Sí | Lectura de correos, reintentos con el SRI y alertas de inventario. |
| 12 | Monitoreo | Sentry Free | Gratis | $0,00 | $0,00 | Sí | Errores del frontend y backend. |
| 13 | Repositorio | GitHub Free | Gratis | $0,00 | $0,00 | Sí | Código fuente y control de versiones. |
| 14 | CI/CD | GitHub Actions | Incluido | $0,00 | $0,00 | Opcional | Pruebas y construcción de imágenes Docker. |
| 15 | Registro de imágenes | GitHub Container Registry (GHCR) | Incluido | $0,00 | $0,00 | Opcional | Guardar las imágenes para que el VPS solo las descargue. |
| 16 | SSL / HTTPS | Let's Encrypt en el proxy inverso del VPS | Incluido | $0,00 | $0,00 | Sí | Certificados HTTPS emitidos y renovados automáticamente. |
| 17 | Gestión de secretos | Variables de entorno del despliegue | Incluido | $0,00 | $0,00 | Sí | Claves API y credenciales; nunca en el repositorio. La `MASTER_ENCRYPTION_KEY` se respalda además en un gestor de contraseñas. |
| 18 | Backups (datos) | Supabase Backups | Incluido en plan | $0,00 | $0,00 | Sí | Recuperar la base de datos ante fallos. |
| 19 | Backups (servidor) | Snapshots del VPS | A cargo del cliente | $0 para el proyecto | $0,00 | Recomendado | Recuperar la configuración del servidor. |
| 20 | Auditoría | Sistema propio + Supabase | Desarrollo propio | $0,00 | $0,00 | Sí | Trazabilidad de acciones de usuarios y operaciones críticas. |
| 21 | Seguridad de archivos | Supabase Storage + políticas de acceso | Incluido | $0,00 | $0,00 | Sí | Proteger XML, PDF e imágenes. |
| 22 | Entorno de pruebas | Segundo despliegue en el mismo VPS (`staging`) | Opcional | $0,00 | $0,00 | Opcional | Validar cambios antes de producción. Usa `SRI_AMBIENTE=1` y otra base de datos. |
| | | | | **Total mensual** | **$60,93** | | |

## Resumen

| Concepto | Antes | Ahora |
|---|---|---|
| Total mensual (sin VPS) | $96,93 | **$60,93** |
| Diferencia | | −$36,00 (Vercel $20 + DigitalOcean $12 + GitHub $4 sin justificar) |

## Notas

- **El costo del VPS lo asume el cliente**, por lo que no se suma al total del proyecto. Si IONDU llegara a contratar el servidor, hay que agregar esa fila.
- **Supabase debe estar en una región cercana al VPS** para no sumar latencia en cada consulta.
- El costo de **OpenAI** es una estimación y depende del consumo; el sistema limita los tokens por empresa (RNF-12).
- Si el cliente no quiere compilar Angular en su servidor, las imágenes se construyen en GitHub Actions y se publican en GHCR (filas 14 y 15, sin costo).
