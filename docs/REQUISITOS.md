# IONDU · Especificación de requerimientos (corregida)

> Extraído de *Proyecto Final Ing. Software I* (capítulo "Especificación de Requerimientos") y actualizado
> para el despliegue en Docker. Los cambios respecto al PDF están marcados con **[CAMBIO]** o **[NUEVO]**.
> Lista completa de correcciones del PDF: [`CORRECCIONES_PDF.md`](CORRECCIONES_PDF.md).

## 1. Contexto

IONDU es una aplicación web progresiva (PWA) para PyMEs ecuatorianas, bajo arquitectura SaaS Multi-Tenant. Integra facturación electrónica, ventas, gastos, inventario, dashboard financiero y un agente de IA que registra información por texto, imagen o voz.

**Usuarios:** *Administrador* (configura la empresa, administra usuarios, ve el dashboard) y *Usuario operativo* (registra ventas, gastos e inventario según sus permisos).

### Restricciones y tecnologías

| Restricción | Descripción |
|---|---|
| Frontend | Angular (PWA). |
| Backend | Python con **FastAPI** **[CAMBIO: el PDF solo decía "Python"]**. |
| Base de datos | PostgreSQL administrado mediante Supabase. |
| Autenticación | Supabase Auth **[CAMBIO: el PDF mezclaba Supabase Auth con una tabla `usuario` propia con contraseñas]**. |
| Despliegue | Contenedores Docker (`docker-compose.yml`) en un VPS administrado por el cliente **[NUEVO]**. |
| Facturación electrónica | Integración con los servicios del SRI. |
| Arquitectura | SaaS Multi-Tenant. |
| IA | API externa (OpenAI). |
| Versionamiento | Repositorio GitHub. |

## 2. Requerimientos funcionales

Prioridad: **P0** = imprescindible para el MVP · **P1** = importante, puede entrar después dentro del MVP.

### Módulo 1 · Usuarios, roles y configuración de la empresa

| ID | Requerimiento | Prio. | Descripción |
|---|---|---|---|
| RF-1.1 | Autenticación segura de usuarios | P0 | Registrar usuarios, iniciar y cerrar sesión, y recuperar la contraseña por correo. |
| RF-1.2 | Gestión de roles y permisos | P0 | Roles mínimos: Administrador y Usuario operativo. El administrador accede a toda la información; el operativo solo a las funciones autorizadas. |
| RF-1.3 | Acceso restringido al dashboard financiero | P0 | Solo el administrador ve el dashboard. Los operativos pueden registrar y confirmar movimientos de inventario y gastos, pero no ver indicadores financieros. |
| RF-1.4 | Configuración de la empresa | P0 | El administrador registra y actualiza: razón social, nombre comercial, RUC, actividad económica, dirección, correo, datos de facturación electrónica y firma electrónica (certificado `.p12`) o credenciales del proveedor. |
| RF-1.5 | Gestión de usuarios internos | P1 | Crear, editar, activar o desactivar usuarios de la empresa. |

### Módulo 2 · Facturación electrónica, ventas e ingresos

| ID | Requerimiento | Prio. | Descripción |
|---|---|---|---|
| RF-2.1 | Emisión de facturas electrónicas | P0 | Generar facturas electrónicas por las ventas del negocio y enviarlas para su autorización ante el SRI. |
| RF-2.2 | Integración con la facturación del SRI | P0 | Emitir facturas, consultar el estado de autorización, recuperar comprobantes emitidos y registrar los datos de la venta. |
| RF-2.3 | Registro automático de ventas | P0 | Cada factura autorizada se registra como venta e ingreso; alimenta ingresos, dashboard, historial de ventas e inventario (si incluye productos registrados). |
| RF-2.4 | Registro manual de ventas | P0 | Para negocios que no facturan todas sus operaciones. Mínimo: fecha, monto, producto o concepto, cantidad, método de pago y observación opcional. |
| RF-2.5 | Actualización automática del inventario por ventas | P0 | Si la venta incluye productos registrados, se descuentan las unidades. |
| RF-2.6 | Historial de ventas | P1 | Filtrar por fecha, cliente, tipo de registro (manual o electrónica), producto y monto. |
| RF-2.7 | Edición o anulación de ventas manuales | P1 | El administrador corrige o anula una venta manual, conservando el historial del cambio. |

### Módulo 3 · Gastos y costos

| ID | Requerimiento | Prio. | Descripción |
|---|---|---|---|
| RF-3.1 | Registro manual de gastos | P0 | Monto, fecha, categoría, proveedor, descripción y método de pago. |
| RF-3.2 | Captura automática de facturas desde el correo | P0 | Conexión al correo del contribuyente (IMAP) para identificar facturas electrónicas y extraer proveedor, fecha, subtotal, impuestos, total, número de comprobante y productos o servicios. **[NUEVO: el proceso es idempotente; un correo o clave de acceso ya procesado no genera un gasto duplicado.]** |
| RF-3.3 | Borrador de gasto desde el correo | P0 | La información extraída genera un borrador que el usuario confirma o corrige antes de guardar. |
| RF-3.4 | Registro de gastos mediante el agente IA | P0 | Por texto, imagen o voz. Ejemplo: "Gasté $25 en empaques". El agente prepara el registro. |
| RF-3.5 | Clasificación de gastos | P0 | Cada gasto tiene categoría (materia prima, servicios, transporte, empaque, mantenimiento, arriendo, otros gastos operativos), elegida por el usuario o sugerida por la IA. |
| RF-3.6 | Historial de gastos | P0 | Filtrar por fecha, categoría, proveedor o monto. |
| RF-3.7 | Edición y eliminación de gastos | P1 | Con trazabilidad de los cambios importantes. |

### Módulo 4 · Productos e inventario

| ID | Requerimiento | Prio. | Descripción |
|---|---|---|---|
| RF-4.1 | Gestión de productos e insumos | P0 | Crear, consultar, editar y desactivar. Tipos: producto para la venta, insumo, o ambos. |
| RF-4.2 | Datos del producto | P0 | Nombre, código interno, categoría, descripción, precio de compra, precio de venta, cantidad disponible, stock mínimo y unidad de medida. |
| RF-4.3 | Control de inventario | P0 | Consultar existencias, sumar, restar, ajustar manualmente y registrar entradas y salidas. |
| RF-4.4 | Actualización cruzada gastos–inventario | P0 | Un gasto de compra de productos registra el gasto y aumenta el inventario en una operación. Ej.: "Compré 5 frascos por $12,50". |
| RF-4.5 | Alta de inventario mediante IA | P0 | Imagen, texto o voz con cantidades; el agente prepara un borrador para crear o actualizar productos. |
| RF-4.6 | Alertas de stock bajo | P0 | Aviso cuando la existencia es igual o inferior al stock mínimo. |
| RF-4.7 | Historial de movimientos | P1 | Entradas, salidas, ventas, compras y ajustes, con fecha, cantidad, tipo, usuario responsable y motivo. |
| RF-4.8 | Ajustes manuales | P1 | El administrador corrige diferencias contra el inventario físico indicando el motivo. |

### Módulo 5 · Dashboard financiero básico

| ID | Requerimiento | Prio. | Descripción |
|---|---|---|---|
| RF-5.1 | Dashboard principal | P0 | Indicadores a partir de ventas, ingresos, gastos e inventario. |
| RF-5.2 | Indicadores básicos | P0 | Ingresos totales, gastos totales, balance o utilidad estimada, ventas registradas, gastos por categoría, estado del inventario y productos con stock bajo. |
| RF-5.3 | Selección de período | P0 | Día actual, semana, mes o rango personalizado. |
| RF-5.4 | Actualización automática | P0 | Se actualiza al confirmarse una operación que afecte ingresos, ventas, gastos o inventario. |
| RF-5.5 | Acceso exclusivo del administrador | P0 | Los indicadores solo son visibles para el administrador. |

### Módulo 6 · Agente IA de captura inteligente

| ID | Requerimiento | Prio. | Descripción |
|---|---|---|---|
| RF-6.1 | Servicio externo de IA | P0 | Servicio basado en consumo de tokens, con límites de uso para controlar costos. |
| RF-6.2 | Entrada por texto | P0 | Instrucciones en lenguaje natural. Ej.: "Agrega 10 cajas al inventario". |
| RF-6.3 | Entrada por imagen | P0 | La IA extrae los datos relevantes de una imagen de gasto, compra o inventario. |
| RF-6.4 | Entrada por voz | P0 | El audio se convierte en texto y se procesa. |
| RF-6.5 | Modificación de gastos | P0 | Crear, modificar, sugerir categorías y corregir antes de guardar. |
| RF-6.6 | Modificación de inventario | P0 | Crear productos, aumentar o disminuir existencias, ajustar y actualizar datos. |
| RF-6.7 | Restricción sobre ingresos | P0 | El agente **no** modifica ingresos. Estos solo se registran por facturación electrónica o venta manual. |
| RF-6.8 | Actualización cruzada entre módulos | P0 | Una interacción puede proponer cambios en varios módulos (gasto + inventario + dashboard). |
| RF-6.9 | Confirmación humana obligatoria | P0 | Todo cambio del agente requiere confirmación antes de guardarse; nunca escribe de forma silenciosa. |
| RF-6.10 | Cuadro de diálogo de confirmación | P0 | Resumen de lo detectado, con opciones Confirmar, Corregir y Cancelar. |
| RF-6.11 | Confirmación por todos los usuarios autorizados | P0 | Cualquier usuario con permiso sobre inventario o gastos puede confirmar. |
| RF-6.12 | Configuración del agente por instrucciones | P0 | Un prompt base define cómo interpretar solicitudes, qué campos extraer, acciones permitidas y prohibidas, y cuándo pedir más información. |
| RF-6.13 | Historial de acciones del agente | P1 | Usuario, fecha, instrucción, datos interpretados y resultado de la confirmación. |
| RF-6.14 | Control de consumo de tokens | P1 | El administrador consulta el consumo aproximado y los límites por empresa o usuario. |

### Módulo 7 · Recomendaciones financieras

| ID | Requerimiento | Prio. | Descripción |
|---|---|---|---|
| RF-7.1 | Análisis general del negocio | P0 | Explicación sencilla de cómo funciona el negocio. |
| RF-7.2 | Recomendaciones básicas | P0 | Sobre disminución de ventas, incremento de gastos, reducción de utilidad, gastos inusuales, stock bajo y rotación de productos. |
| RF-7.3 | Sin modificación automática | P0 | Son informativas; no cambian ingresos, gastos ni inventario sin nueva confirmación. |
| RF-7.4 | Explicación de las recomendaciones | P1 | Cada una indica qué información se usó. |

### Requerimientos que pasan a la versión 1.1

Score financiero de 1 a 100 · proyección anual avanzada · optimización fiscal · estimación avanzada del IVA · calendario tributario completo · alertas tributarias automatizadas · comparaciones financieras avanzadas · reportes programados por correo · exportación a PDF y Excel · integraciones bancarias · aplicación móvil nativa · modelo propio de IA · aprendizaje a partir de correcciones del usuario · reconocimiento avanzado de PDF y Excel mediante IA.

### Justificación de la priorización

El MVP se concentra en cinco elementos: facturación electrónica y ventas, control de gastos, inventario, dashboard básico y agente IA. Las ventas pueden registrarse desde el facturador o manualmente, para que negocios muy pequeños usen el sistema desde el inicio. El agente IA es el principal diferenciador, pero todas sus acciones requieren confirmación humana. El análisis fiscal avanzado, la predicción y la automatización tributaria se postergan para reducir el alcance.

## 3. Requerimientos no funcionales (clasificación de Sommerville)

| ID | Requerimiento | Clasificación | Criterio de validación |
|---|---|---|---|
| RNF-01 | Responder cualquier consulta en máximo 2 s para operaciones normales. | Producto – Rendimiento | 100 consultas; el 95 % responde en ≤ 2 s. |
| RNF-02 | El registro de ventas, gastos e inventario se completa en máximo 3 s. | Producto – Rendimiento | Registrar 100 operaciones y medir el tiempo promedio. |
| RNF-03 | Disponibilidad del 99,5 % mensual. | Producto – Disponibilidad | **[CAMBIO]** Medir con un monitor de uptime externo sobre `/api/health` y el healthcheck de los contenedores (antes: "reportes del proveedor cloud"). |
| RNF-04 | Soportar al menos 100 usuarios concurrentes sin degradación significativa. | Producto – Capacidad | Pruebas de carga con 100 usuarios concurrentes. |
| RNF-05 | Toda comunicación cliente–servidor usa HTTPS. | Producto – Seguridad | Todo el tráfico usa certificados SSL/TLS válidos (Let's Encrypt en el proxy del VPS). |
| RNF-06 | Las contraseñas se almacenan con algoritmos de hash seguros. | Producto – Seguridad | **[CAMBIO]** Las gestiona Supabase Auth; verificar que IONDU no almacene contraseñas propias. |
| RNF-07 | Copias de seguridad automáticas diarias. | Producto – Confiabilidad | Verificar los respaldos de Supabase y hacer una restauración de prueba. |
| RNF-08 | La aplicación es responsive (computadoras, tablets, teléfonos). | Producto – Usabilidad | Probar en escritorio y móvil sin pérdida de funcionalidad. |
| RNF-09 | Mantener la integridad de la información en cualquier operación de la IA. | Producto – Integridad | Pruebas donde la IA propone cambios; solo se guardan tras la confirmación. |
| RNF-10 | Navegación consistente en todos los módulos. | Producto – Usabilidad | Evaluación heurística de menús, botones y formularios. |
| RNF-11 | Historial de todas las operaciones de usuarios y del agente IA. | Producto – Auditoría | Cada modificación genera registro con usuario, fecha, acción y módulo. |
| RNF-12 | Limitar el consumo de tokens del agente según lo configurado por el administrador. | Producto – Restricciones | Configurar un límite y comprobar que no se pueda exceder. |
| RNF-13 | Desarrollo con Angular (frontend) y Python (backend). | Organizacional – Estándares | Revisar el repositorio. |
| RNF-14 | PostgreSQL como motor de base de datos mediante Supabase. | Organizacional – Plataforma | **[CAMBIO]** Revisar la conexión por el *Session Pooler* de Supabase (IPv4); el PDF mezclaba MySQL y PostgreSQL. |
| RNF-15 | Todo el código se administra en GitHub. | Organizacional – Proceso | Existencia del repositorio e historial de commits. |
| RNF-16 | **[CAMBIO]** El sistema se empaqueta en contenedores Docker y se despliega con `docker-compose.yml` en un VPS administrado por el cliente, con HTTPS automático. | Organizacional – Infraestructura | `docker compose up` levanta el sistema completo; todos los servicios reportan *healthy*. (Antes: "infraestructura cloud previamente definida", que implicaba Vercel y DigitalOcean.) |
| RNF-17 | Cumplir los requisitos técnicos del SRI para comprobantes electrónicos. | Externo – Legal | Emitir una factura de prueba y verificar que el SRI la acepte. |
| RNF-18 | Firma digital válida y vigente proporcionada por la empresa cliente. | Externo – Legal | Verificar la vigencia del certificado y firmar de prueba. |
| RNF-19 | Cumplir la normativa tributaria ecuatoriana de facturación electrónica. | Externo – Regulaciones | Validar la estructura del XML y que sea autorizado por el SRI. |
| RNF-20 | Tratar los datos personales conforme a la Ley Orgánica de Protección de Datos Personales. | Externo – Legal | Revisar políticas de tratamiento de datos y auditar el cumplimiento. |
| RNF-21 | **[NUEVO]** Los contenedores no guardan estado: archivos y certificados viven en Supabase, no en el disco del contenedor. | Organizacional – Infraestructura | Recrear los contenedores no pierde información. |
| RNF-22 | **[NUEVO]** Los certificados `.p12`, sus contraseñas y las credenciales IMAP se almacenan cifrados (AES-GCM); la llave maestra solo existe como variable de entorno. | Producto – Seguridad | Revisar la base de datos: ningún certificado ni credencial aparece en claro. |
| RNF-23 | **[NUEVO]** El aislamiento entre empresas se aplica en la aplicación (`id_empresa`) y en la base de datos mediante *Row Level Security*. | Producto – Seguridad | Prueba: una consulta sin filtro de empresa no devuelve datos de otra empresa. |
| RNF-24 | **[NUEVO]** Ningún secreto se guarda en el repositorio; la configuración se lee de variables de entorno. | Organizacional – Proceso | Revisar el historial de git; solo existe `.env.example`. |
| RNF-25 | **[NUEVO]** El sistema alerta cuando un certificado `.p12` está próximo a vencer. | Producto – Confiabilidad | Con un certificado a < 30 días de vencer, se muestra la alerta al administrador. |
