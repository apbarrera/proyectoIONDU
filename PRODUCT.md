# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
- **Administrador (dueño/a de la PyME):** configura la empresa, administra usuarios, ve el dashboard financiero (acceso exclusivo) y decide con base en él.
- **Usuario operativo:** registra ventas, gastos e inventario a diario según sus permisos; no ve indicadores financieros.
- Ambos pesan por igual en las decisiones de interfaz. Contexto: PyMEs ecuatorianas, personas sin formación contable que comparten computadoras y también usan el celular.

## Product Purpose
IONDU es una PWA SaaS multi-tenant que integra facturación electrónica del SRI, ventas, gastos, inventario, dashboard financiero y un agente de IA que captura información por texto, imagen o voz. Éxito: que una PyME pequeña lleve sus cuentas completas sin esfuerzo contable y sin errores de registro.

## Positioning
Dos diferenciales, ambos centrales: (1) un agente de IA que propone registros pero nunca guarda sin confirmación humana y jamás toca ingresos; (2) todo en un solo lugar y pensado para Ecuador (SRI, `America/Guayaquil`), con ventas y facturación unidas en un solo módulo.

## Operating Context
- Facturas electrónicas firmadas con certificado `.p12` del cliente (XAdES-BES), autorizadas por el SRI.
- Facturas de proveedores leídas por correo (IMAP) que generan borradores de gasto.
- Despliegue en Docker en un VPS del cliente con Coolify; base de datos PostgreSQL en Supabase; multi-tenant por `id_empresa`.
- Equipos compartidos: al cerrar sesión se limpia todo el almacenamiento local y la caché del service worker.

## Capabilities and Constraints
- Módulos: usuarios y roles, ventas y facturación (interruptor "Emitir factura electrónica" activado por defecto), gastos, inventario, dashboard, agente IA, recomendaciones.
- La IA nunca crea ni altera ingresos; toda acción sobre inventario o gastos exige confirmación explícita (Confirmar, Corregir, Cancelar).
- Dashboard solo para `Administrador`.
- Todas las peticiones HTTP usan rutas relativas `/api/...`.
- Hoy el frontend usa datos de ejemplo (*mock*); el backend es un esqueleto sin lógica de negocio.
- Terminología: Administrador, Usuario operativo, venta, gasto, factura autorizada / en proceso / rechazada / sin factura.

## Brand Commitments
- Nombre IONDU. Acento morado único sobre blanco y negro, tema claro y oscuro (sigue al sistema).
- Tipografía Geist incluida en la app; íconos Phosphor; logo vectorizado (pendiente de sustituir por el SVG original del diseño).
- Voz en español de Ecuador: clara, directa y sin jerga contable.

## Evidence on Hand
- `docs/REQUISITOS.md`, `docs/DECISIONES.md`, `docs/ESTADO.md`, `docs/PRESUPUESTO.md`, `docs/DESPLIEGUE.md` y el PDF del proyecto.
- Usuarios de prueba: `admin@iondu.demo` y `operador@iondu.demo`.
- No hay clientes reales, testimonios ni métricas de uso; no inventarlos.

## Product Principles
1. **Nada se guarda sin que una persona lo confirme** cuando interviene la IA; los ingresos solo entran por factura o venta manual.
2. **Una sola vía para vender y facturar:** el módulo evita que la gente elija a mano qué facturar.
3. **Aislamiento total entre empresas:** ningún dato cruza el límite de `id_empresa`.
4. **Pensado para quien no es contable:** lenguaje llano y estados que se entienden sin explicación.
5. **Funciona en el equipo que haya:** móvil, computadora compartida, sin conexión estable.

## Accessibility & Inclusion
Meta: 100 en Lighthouse de accesibilidad en todas las pantallas, en ambos temas y en móvil. Etiquetas vinculadas, contraste suficiente, foco atrapado en modales, objetivos táctiles de al menos 24 px, operable por teclado y respeto de "reducir movimiento".
