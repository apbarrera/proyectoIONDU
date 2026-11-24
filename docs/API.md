# IONDU · Contrato de la API

> Qué datos viajan entre el frontend y el backend. Si cambia un endpoint, se actualiza aquí **antes** de programarlo.
> Estado de cada endpoint: ✅ disponible · 🚧 en construcción · ⏳ pendiente de una decisión.
> La documentación interactiva está en `/api/docs` (solo fuera de producción).

## 1. Reglas generales

- **Rutas relativas** bajo `/api/...` (Nginx las reenvía a la API). Nombres de rutas y del JSON en **inglés**, con
  el estilo del frontend (`camelCase`); la base de datos sigue en español y el backend traduce.
- **Empresa (multi-tenant):** cada petición trabaja solo con los datos de la empresa del usuario. Nunca se envía
  `id_empresa` en el cuerpo ni en la ruta.
  - **Con sesión:** encabezado `Authorization: Bearer <token>` (el `access_token` de Supabase Auth). La empresa y
    el rol salen de las pertenencias del usuario (tabla `usuario_empresa`). Un usuario **puede pertenecer a varias
    empresas**: si tiene una sola, se usa esa; si tiene varias, el frontend envía también `X-Empresa-Id` con la
    elegida, y el backend comprueba que el usuario pertenezca a ella. Ver sección 5.
  - **Sin sesión, solo desarrollo:** encabezado `X-Empresa-Id: <número>`, con rol Administrador, para probar sin
    login. En cualquier otro entorno se responde `401`.
  - **Usuario demo, solo desarrollo:** además de `X-Empresa-Id`, el encabezado `X-Usuario-Id: <uuid>` actúa como
    ese usuario con su pertenencia real (rol y nombre), así se pueden registrar ventas, gastos y movimientos desde
    Swagger sin Supabase. `backend/scripts/cargar_datos_demo.py` crea el Administrador
    `11111111-1111-1111-1111-111111111111` y el Operativo `22222222-2222-2222-2222-222222222222`. En producción se ignora.
- **IDs:** números enteros (`"id": 12`). *En el frontend hoy son texto (`id: string`); hay que cambiarlos a `number`.*
- **Montos y cantidades:** números con hasta 2 decimales (`"salePrice": 2.5`).
- **Fechas:** texto ISO 8601 con zona horaria de Ecuador (`"2026-10-25T14:30:00-05:00"`).
- **Listas con páginas:** igual que `PageResult` del frontend.

  ```json
  { "items": [ ... ], "total": 57, "page": 1, "pageSize": 20 }
  ```
  Parámetros: `page` (desde 1, por defecto 1) y `pageSize` (por defecto 20, máximo 100).

## 2. Errores

Todo error responde con la misma forma, para que el frontend lo muestre sin casos especiales:

```json
{
  "error": {
    "code": "PRODUCT_SKU_TAKEN",
    "message": "Ya existe un producto con el código ABC-001.",
    "details": []
  }
}
```

- `code`: identificador fijo para el programa (no cambia aunque cambie el texto).
- `message`: texto en español que se puede mostrar al usuario.
- `details`: solo en errores de validación; un elemento por campo.

  ```json
  "details": [ { "field": "salePrice", "message": "Debe ser mayor o igual a 0." } ]
  ```

| HTTP | `code` | Cuándo |
|---|---|---|
| 400 | `BAD_REQUEST` | El cuerpo no es un JSON válido o no está en UTF-8 |
| 401 | `UNAUTHENTICATED` | Falta identificar al usuario o la empresa |
| 403 | `FORBIDDEN`, `NO_COMPANY`, `COMPANY_ACCESS_DENIED` | Se sabe quién es el usuario, pero no puede hacer esto (ver sección 5) |
| 404 | `NOT_FOUND` | El recurso no existe **o es de otra empresa** (no se revela cuál de las dos) |
| 409 | `PRODUCT_SKU_TAKEN`, `COMPANY_SELECTION_REQUIRED`, … | Choca con un dato existente, o falta elegir empresa (sección 5) |
| 422 | `VALIDATION_ERROR` | Datos con formato o valores inválidos (ver `details`) |
| 503 | `DATABASE_UNAVAILABLE` | La base de datos no responde |
| 500 | `INTERNAL_ERROR` | Error inesperado (el detalle queda en los registros del servidor, no en la respuesta) |

## 3. Categorías de producto

### Objeto `ProductCategory`

| Campo | Tipo | Columna en la base | Notas |
|---|---|---|---|
| `id` | number | `id_categoria_producto` | Solo lectura |
| `name` | string (1–100) | `nombre` | Obligatorio |
| `description` | string \| null (≤255) | `descripcion` | Opcional |

### Endpoints

| Estado | Método y ruta | Qué hace | Respuesta |
|---|---|---|---|
| ✅ | `GET /api/product-categories` | Todas las categorías de la empresa, ordenadas por nombre (sin páginas: son pocas) | `200` con `ProductCategory[]` |
| ✅ | `POST /api/product-categories` | Crea una categoría. Cuerpo: `{ "name", "description"? }` | `201` con `ProductCategory` |

## 4. Productos

### Objeto `Product`

| Campo | Tipo | Columna en la base | Notas |
|---|---|---|---|
| `id` | number | `id_producto` | Solo lectura |
| `sku` | string (1–25) | `codigo_principal` | Obligatorio; código interno del producto. Máximo 25 porque es el límite de `codigoPrincipal` en el XML de la factura del SRI |
| `name` | string (1–150) | `nombre` | Obligatorio |
| `description` | string \| null | `descripcion` | Opcional |
| `categoryId` | number | `id_categoria_producto` | Obligatorio; debe ser una categoría de la misma empresa |
| `categoryName` | string | `categoria_producto.nombre` | Solo lectura, para mostrar en tablas |
| `type` | `"venta"` \| `"insumo"` \| `"ambos"` | `tipo` | ⏳ Provisional (RF-4.1); por defecto `"venta"` |
| `unit` | string (1–20) | `unidad_medida` | Por defecto `"UNIDAD"` |
| `salePrice` | number ≥ 0 | `precio_venta` | Por defecto 0 (un insumo que no se vende queda en 0) |
| `cost` | number ≥ 0 | `precio_compra` | Por defecto 0 |
| `appliesVat` | boolean | `aplica_iva` | Por defecto `true`; necesario para facturar |
| `currentStock` | number | `stock_actual` | **Solo se fija al crear** (≥ 0, por defecto 0). Después cambia por ventas, compras y ajustes de inventario, nunca editando el producto |
| `minStock` | number ≥ 0 \| null | `stock_minimo` | Opcional; sin valor, no hay alerta |
| `lowStock` | boolean | (calculado) | Solo lectura; `true` si `minStock` tiene valor y `currentStock ≤ minStock` (RF-4.6) |
| `active` | boolean | `producto.activo` | Lectura y edición; por defecto `true` (RF-4.1) |

Ejemplo:

```json
{
  "id": 12,
  "sku": "CAF-250",
  "name": "Café molido 250 g",
  "description": null,
  "categoryId": 3,
  "categoryName": "Bebidas",
  "type": "venta",
  "unit": "UNIDAD",
  "salePrice": 4.5,
  "cost": 2.8,
  "appliesVat": true,
  "currentStock": 18,
  "minStock": 5,
  "lowStock": false
}
```

### Endpoints

| Estado | Método y ruta | Qué hace | Respuesta |
|---|---|---|---|
| ✅ | `GET /api/products` | Lista con páginas, ordenada por nombre. Filtros opcionales: `search` (busca en `sku` y `name`), `categoryId`, `type`, `lowStock=true` | `200` con `PageResult<Product>` |
| ✅ | `GET /api/products/{id}` | Un producto | `200` con `Product`, o `404` |
| ✅ | `POST /api/products` | Crea un producto. Cuerpo: todos los campos editables (`sku`, `name`, `categoryId` obligatorios) y `currentStock` inicial | `201` con `Product`; `409 PRODUCT_SKU_TAKEN` si el código ya existe en la empresa; `422 CATEGORY_NOT_FOUND` si la categoría no existe |
| ✅ | `PATCH /api/products/{id}` | Modifica solo los campos enviados. **No acepta `currentStock`** | `200` con `Product`; mismos errores que al crear, y `404` |
| ✅ | Desactivar / reactivar | `PATCH` con `{ "active": false }` o `{ "active": true }` | Disponible; los productos inactivos siguen visibles en el listado |

No hay `DELETE`: un producto con ventas o movimientos no se puede borrar sin romper el historial; se desactiva.

## 5. Sesión

El frontend inicia sesión con Supabase Auth y envía su `access_token` en cada petición:
`Authorization: Bearer <token>`. El backend verifica la firma (llaves públicas de Supabase), el vencimiento, el
proyecto (`iss`) y que sea de un usuario autenticado (`aud`). Luego busca su empresa y su rol en `usuario_empresa`
(solo usuarios con estado `ACTIVO`).

| Estado | Método y ruta | Qué hace | Respuesta |
|---|---|---|---|
| ✅ | `GET /api/me/companies` | Empresas activas del usuario, con su rol en cada una. **No** exige haber elegido empresa: sirve para mostrar el selector | `200` con `CompanyOption[]` |
| ✅ | `GET /api/me` | Perfil del usuario en la empresa de la petición. Sirve para comprobar que el login funciona de punta a punta | `200` con `Me` |

Objeto `Me` (mismos campos que `User` del frontend, `core/models/user.model.ts`):

```json
{
  "id": "6f1c2a1e-…",
  "email": "ana@empresa.ec",
  "fullName": "Ana Torres",
  "role": "admin",
  "tenantId": 7,
  "active": true
}
```

`role` es `"admin"` para el rol Administrador y `"operator"` para Operativo. `tenantId` es el `id_empresa`.

Objeto `CompanyOption`:

```json
{ "id": 7, "name": "CAFETERÍA DEMO S.A.", "tradeName": "Café Demo", "ruc": "1790010937001", "role": "admin" }
```

**Flujo de inicio de sesión:**

1. Login con Supabase Auth (`signInWithPassword`).
2. `GET /api/me/companies`. Si devuelve **una** empresa, se usa esa. Si devuelve **varias**, se muestra el
   selector y desde ahí toda petición lleva `X-Empresa-Id: <id elegido>` (se puede cambiar de empresa en cualquier
   momento). Si devuelve **ninguna**, mostrar "tu usuario no tiene acceso".
3. `GET /api/me` (con `X-Empresa-Id` si corresponde) para el perfil y el rol en esa empresa.

Errores de sesión:

| HTTP | `code` | Cuándo | Qué hacer en el frontend |
|---|---|---|---|
| 401 | `UNAUTHENTICATED` | Sin token, token inválido o de otro proyecto | Ir al login |
| 401 | `TOKEN_EXPIRED` | El token venció | Renovar la sesión con Supabase (`refreshSession`) y reintentar; si falla, ir al login |
| 403 | `NO_COMPANY` | El usuario no tiene empresa asignada o está inactivo | Mostrar "tu usuario no tiene acceso; contacta al administrador" |
| 403 | `COMPANY_ACCESS_DENIED` | `X-Empresa-Id` es de una empresa a la que el usuario no pertenece (o su pertenencia está inactiva) | Volver al selector de empresa |
| 403 | `FORBIDDEN` | Su rol no permite esa acción (por ejemplo, el dashboard es solo para Administrador) | Ocultar o bloquear esa opción |
| 409 | `COMPANY_SELECTION_REQUIRED` | El usuario tiene varias empresas y no envió `X-Empresa-Id` | Mostrar el selector de empresa |
| 503 | `AUTH_UNAVAILABLE` | No se pudieron obtener las llaves de Supabase | Mostrar "intenta en un momento" |

## 6. Certificado de firma electrónica de la empresa

| Estado | Método y ruta | Qué hace | Respuesta |
|---|---|---|---|
| ✅ | `PUT /api/company/certificate` | **Solo Administrador.** Sube el `.p12` de la empresa con su contraseña. Se valida (contraseña, no vencido) y se guarda **cifrado**; nunca se escribe en disco | `200` con `{ "mensaje", "fecha_vencimiento" }` |

Se envía como formulario `multipart/form-data` con dos campos: `archivo` (el `.p12`, máximo 5 MiB) y `clave`.
Errores: `422` si el archivo no es `.p12`, supera el tamaño, la contraseña es incorrecta o el certificado está
vencido; `403` si el usuario no es Administrador.

## 7. Clientes

En la venta se escribe la cédula o el RUC del cliente; si ya existe, se autocompletan sus datos (`lookup`). El
**consumidor final** (`9999999999999`) no se guarda como cliente: se usa directamente en la venta.

### Objeto `Customer`

| Campo | Tipo | Columna en la base | Notas |
|---|---|---|---|
| `id` | number | `id_cliente` | Solo lectura |
| `identificationType` | `"cedula"` \| `"ruc"` \| `"pasaporte"` \| `"exterior"` | `tipo_identificacion` (código SRI `05`, `04`, `06`, `08`) | Opcional al crear: con 10 dígitos se toma cédula; con 13, RUC |
| `identification` | string | `identificacion` | Obligatorio; validado con las reglas del SRI (dígito verificador, provincia, etc.) |
| `name` | string (1–255) | `nombre_razon_social` | Obligatorio |
| `address` | string \| null | `direccion` | Opcional |
| `phone` | string \| null (≤20) | `telefono` | Opcional |
| `email` | string \| null (≤150) | `correo_electronico` | Opcional; si tiene, se le envía la factura |
| `identificationWarning` | string \| null | (calculado) | Solo lectura. Aviso si el RUC de una sociedad no cumple el dígito verificador clásico (se acepta igual, `DECISIONES.md` 2.16) |

### Endpoints

| Estado | Método y ruta | Qué hace | Respuesta |
|---|---|---|---|
| ✅ | `GET /api/customers` | Lista con páginas, ordenada por nombre. Filtro `search` (en identificación y nombre) | `200` con `PageResult<Customer>` |
| ✅ | `GET /api/customers/lookup?identification=…` | Busca por cédula, RUC o pasaporte exactos (para autocompletar en la venta) | `200` con `Customer`, o `404` |
| ✅ | `GET /api/customers/{id}` | Un cliente | `200` con `Customer`, o `404` |
| ✅ | `POST /api/customers` | Crea un cliente | `201` con `Customer`; `409 CUSTOMER_EXISTS` si ya existe esa identificación en la empresa; `422` si la identificación no es válida |
| ✅ | `PATCH /api/customers/{id}` | Modifica solo los campos enviados | `200` con `Customer`; mismos errores que al crear |

No hay `DELETE`: un cliente con ventas o facturas no se puede borrar sin romper el historial.

## 8. Ventas

Registrar una venta **exige sesión** (`Authorization: Bearer`): la venta guarda qué usuario la hizo. Con el encabezado de desarrollo `X-Empresa-Id` se pueden consultar, pero no registrar (`403 USER_SESSION_REQUIRED`).

Una venta admite líneas de **productos** y de **concepto libre** (servicios u otros conceptos sin producto). En las líneas de producto, el backend obtiene el precio y el código de IVA desde el producto. En las líneas de concepto libre, el frontend envía descripción, precio unitario y código de IVA. El código de IVA se conserva como dato histórico en cada detalle de venta.

Los totales se calculan con las reglas del SRI (decisión 2.18), usando aritmética decimal y redondeo comercial.

### Registrar: `POST /api/sales`

Ejemplo con una línea de producto y otra de concepto libre:

```json
{
  "customerId": 5,
  "items": [
    { "productId": 12, "quantity": 2, "discount": 0 },
    {
      "description": "Servicio de instalación",
      "quantity": 1,
      "unitPrice": 15.00,
      "vatPercentageCode": "4",
      "discount": 0
    }
  ],
  "paymentMethod": "efectivo",
  "observation": "Entrega a domicilio"
}
```

| Campo | Tipo | Notas |
|---|---|---|
| `customerId` | number \| null | Un cliente de la empresa (sección 7). `null` = consumidor final |
| `items` | lista (1–200) | Líneas de producto o concepto libre |
| `items[].productId` | number \| null | Para una línea de producto: producto activo de tipo `venta` o `ambos`. Si se omite o es `null`, la línea se interpreta como concepto libre |
| `items[].quantity` | number > 0 | Hasta 4 decimales |
| `items[].discount` | number ≥ 0 | Descuento en dólares de esa línea; por defecto 0, hasta 2 decimales |
| `items[].description` | string | Obligatorio para concepto libre; hasta 255 caracteres |
| `items[].unitPrice` | number ≥ 0 | Obligatorio para concepto libre; hasta 4 decimales |
| `items[].vatPercentageCode` | string | Obligatorio para concepto libre. Códigos admitidos: `"0"` (0 %), `"4"` (15 %), `"5"` (5 %), `"6"` (no objeto de IVA) y `"7"` (exento de IVA) |
| `paymentMethod` | `"efectivo"` \| `"tarjeta_debito"` \| `"tarjeta_credito"` \| `"transferencia"` | Se separa la tarjeta en débito y crédito porque el SRI las distingue |
| `observation` | string \| null (≤255) | Opcional |

**Reglas de las líneas:**
- Una línea de producto envía `productId`, `quantity` y, opcionalmente, `discount`. No debe enviar `description`, `unitPrice` ni `vatPercentageCode`: esos datos se obtienen del producto.
- Una línea de concepto libre no envía `productId` y debe incluir `description`, `quantity`, `unitPrice` y `vatPercentageCode`.
- Un mismo producto no puede repetirse en la lista. Las líneas de concepto libre no están sujetas a esa restricción.
- El descuento no puede superar el importe bruto de su línea.

En una sola transacción (se guarda todo o nada), se crea la venta y sus líneas. **Solo las líneas de producto descuentan stock** y generan su movimiento de inventario (`VENTA`). Las líneas de concepto libre no modifican el inventario.

Respuestas: `201` con `Sale`; `409 INSUFFICIENT_STOCK` si no alcanza el stock (con el producto en `details`); `422` si un producto o cliente no existe en la empresa, está inactivo, no se vende, los datos de una línea son inválidos o el descuento supera el importe bruto; `403 USER_SESSION_REQUIRED` sin sesión de usuario.

### Objeto `Sale`

```json
{
  "id": 31,
  "date": "2026-11-03T15:20:00-05:00",
  "customerId": 5,
  "customerName": "Juan Pérez",
  "customerIdentification": "1710000009",
  "items": [
    {
      "productId": 12,
      "sku": "CAF-250",
      "productName": "Café molido 250 g",
      "quantity": 2,
      "unitPrice": 4.5,
      "discount": 0,
      "vatPercentageCode": "4",
      "subtotal": 9.0
    },
    {
      "productId": null,
      "sku": null,
      "productName": "Servicio de instalación",
      "quantity": 1,
      "unitPrice": 15.0,
      "discount": 0,
      "vatPercentageCode": "4",
      "subtotal": 15.0
    }
  ],
  "subtotal": 24.0,
  "ivaAmount": 3.6,
  "total": 27.6,
  "paymentMethod": "efectivo",
  "status": "completada",
  "observation": "Entrega a domicilio"
}
```

En la respuesta, `vatPercentageCode` representa el código de IVA guardado en cada detalle. Para las líneas de concepto libre, `productId` y `sku` son `null`, y `productName` contiene la descripción registrada.

Sin cliente: `customerId` y `customerIdentification` son `null` y `customerName` es `"CONSUMIDOR FINAL"`.

### Consultar

| Estado | Método y ruta | Qué hace | Respuesta |
|---|---|---|---|
| ✅ | `POST /api/sales` | Registra la venta (arriba) | `201` con `Sale` |
| ✅ | `GET /api/sales` | Historial, de la más reciente a la más antigua. Filtros: `from` y `to` (fechas `AAAA-MM-DD`, en hora de Ecuador), `customerId`, `paymentMethod` | `200` con `PageResult<Sale>` |
| ✅ | `GET /api/sales/{id}` | Una venta | `200` con `Sale`, o `404` |
| ✅ | `POST /api/sales/{id}/invoice` | **Emite la factura electrónica** de la venta: XML, firma con el `.p12` de la empresa, envío al SRI y RIDE. Exige sesión | `201` con `Invoice` |
| ✅ | `GET /api/sales/{id}/invoice/ride` | Descarga el PDF (RIDE) de la factura. Exige sesión | `200` con `application/pdf` |

Pendiente: anular ventas (RF-2.7) y completar la integración para emitir facturas electrónicas desde una venta.

## 9. Cambios que implica en el frontend

1. `Product.id`: de `string` a `number`.
2. `category` (texto libre) pasa a ser `categoryId` (elegir de `GET /api/product-categories`) y `categoryName` (para mostrar).
3. `type`: valores según la decisión pendiente (hoy el frontend usa `simple`, `insumo`, `compuesto`).
4. Campos nuevos: `description`, `appliesVat`, `lowStock`.
5. El formulario de edición no debe cambiar `currentStock`; eso se hace desde Ajustes o Movimientos.
6. En `ProductsService`, reemplazar `simulateRequest(...)` por `HttpClient` contra estas rutas.
7. Login: `AuthService.login` usa Supabase Auth (`signInWithPassword`), luego `GET /api/me/companies` (selector
   si hay varias empresas) y `GET /api/me` para obtener el `User` (mismos campos). `User.tenantId` pasa de
   `string` a `number`. Ver el flujo en la sección 5.
8. Un interceptor HTTP agrega `Authorization: Bearer <access_token>` (y `X-Empresa-Id` si el usuario eligió
   empresa) a toda petición a `/api/...`, y maneja `TOKEN_EXPIRED`, `NO_COMPANY`, `COMPANY_SELECTION_REQUIRED` y
   `COMPANY_ACCESS_DENIED` (sección 5).
9. El `sku` admite máximo 25 caracteres (sección 4).
10. Nueva venta: al escribir la cédula o el RUC, `GET /api/customers/lookup` autocompleta el cliente; si no existe,
    `POST /api/customers` lo crea. El consumidor final debe ser `9999999999999` (13 nueves), no `9999999999`.
11. `SalesService.createSale` envía `customerId` (no el nombre), `items` con `productId` y `quantity` (sin precio)
    y `paymentMethod` con tarjeta separada en `tarjeta_debito` / `tarjeta_credito` (sección 8).

**Estado de estos cambios en el frontend (24/11/2026):** ✅ los puntos 7, 8 (login e interceptor), 10 y 11 y la
emisión de facturas (`POST /api/sales/{id}/invoice` y su RIDE) están hechos; el 6 está hecho solo en la pantalla de
Productos. Siguen pendientes los puntos 1 a 5 (IDs numéricos, `categoryId` en todos los consumidores, tipos de
producto, campos nuevos y bloqueo de `currentStock` en el resto de las pantallas). Detalle por módulo en
[`ESTADO.md`](ESTADO.md), sección "Frontend: conexión con la API".

**Pendiente del backend** detectado al conectar la facturación: `Sale` no trae el estado de su factura ni
`createdBy`, no hay `GET` de facturas y una factura rechazada no se puede reintentar (`409`). Lista completa en
`ESTADO.md`, sección 2.G.

## 10. Empresa y configuración de facturación

Cualquier usuario de la empresa puede consultarlas; **solo el Administrador las modifica** (`403 FORBIDDEN`).

| Estado | Método y ruta | Qué hace | Respuesta |
|---|---|---|---|
| ✅ | `GET /api/company` | Datos de la empresa, estado de la firma y configuración de facturación | `200` con `Company` |
| ✅ | `PUT /api/company` | Edita solo los campos enviados: `businessName`, `tradeName`, `economicActivity`, `address`, `email`. **El RUC no se edita** (va dentro de cada clave de acceso) | `200` con `Company` |
| ✅ | `PUT /api/company/billing-settings` | Guarda la configuración del emisor (objeto `BillingSettings` completo) | `200` con `Company` |

Objeto `Company` (mismos nombres que `Tenant` del frontend):

```json
{
  "id": 7, "ruc": "1790010937001", "businessName": "CAFETERÍA DEMO S.A.", "tradeName": "Café Demo",
  "economicActivity": "Venta de café", "address": "Av. Amazonas N12-34, Quito", "email": "demo@iondu.ec",
  "electronicSignature": { "configured": true, "expiresAt": "2027-03-01", "expiresSoon": false, "expired": false },
  "billing": {
    "environment": "pruebas", "establishment": "001", "emissionPoint": "001",
    "requiredToKeepAccounts": false, "rimpe": true, "specialTaxpayer": null
  }
}
```

- `electronicSignature.expiresSoon` es `true` cuando faltan 30 días o menos (alerta de RNF-25).
- `billing` es `null` mientras la empresa no configure su facturación; sin ella no se puede emitir.
- `environment`: `pruebas` (SRI de pruebas, sin validez legal) o `produccion`. `establishment` y `emissionPoint`:
  3 dígitos. `specialTaxpayer`: número de resolución de contribuyente especial, o `null`.

## 11. Gastos, categorías de gasto y proveedores

Cualquier usuario de la empresa puede consultarlos y registrarlos. **Registrar o editar un gasto exige
iniciar sesión** (`403 USER_SESSION_REQUIRED`): el gasto guarda qué usuario lo registró.

### Categorías de gasto

La primera vez que se piden se crean solas las 7 de RF-3.5: Materia prima, Servicios, Transporte,
Empaque, Mantenimiento, Arriendo y Otros gastos operativos (`predefined: true`).

| Estado | Método y ruta | Qué hace | Respuesta |
|---|---|---|---|
| ✅ | `GET /api/expense-categories` | Lista las categorías por nombre (sin paginar) | `200` con `ExpenseCategory[]` |
| ✅ | `POST /api/expense-categories` | Crea una propia: `{ "name", "description"? }`. Nombre repetido (sin importar mayúsculas) → `409 CATEGORY_EXISTS` | `201` con `ExpenseCategory` |

```json
{ "id": 3, "name": "Servicios", "description": null, "predefined": true }
```

### Proveedores

| Estado | Método y ruta | Qué hace | Respuesta |
|---|---|---|---|
| ✅ | `GET /api/suppliers?page=&pageSize=&search=` | Lista paginada; `search` busca en identificación y nombre | `200` con `Page<Supplier>` |
| ✅ | `GET /api/suppliers/lookup?identification=` | Busca por RUC o cédula exactos (para autocompletar) | `200` o `404` |
| ✅ | `GET /api/suppliers/{id}` | Un proveedor | `200` o `404` |
| ✅ | `POST /api/suppliers` | Crea: `identification`, `name`, `phone`?, `email`?, `address`? | `201` con `Supplier` |
| ✅ | `PATCH /api/suppliers/{id}` | Edita solo los campos enviados | `200` con `Supplier` |

```json
{
  "id": 4, "identification": "1790016919001", "name": "Corporación Favorita", "phone": "022345678",
  "email": "compras@favorita.ec", "address": "Quito", "identificationWarning": null
}
```

- `identification`: RUC (13 dígitos) o cédula (10), validados con las reglas del SRI; si no →
  `422 INVALID_IDENTIFICATION`. Repetida en la empresa → `409 SUPPLIER_EXISTS`.
- `identificationWarning`: aviso (no error) para RUC de sociedades cuyo dígito verificador no cuadra.

### Gastos

| Estado | Método y ruta | Qué hace | Respuesta |
|---|---|---|---|
| ✅ | `GET /api/expenses` | Lista paginada, el más reciente primero. Filtros: `from`, `to` (fechas `YYYY-MM-DD` de Ecuador), `categoryId`, `supplierId`, `paymentMethod`, `minTotal`, `maxTotal` | `200` con `Page<Expense>` |
| ✅ | `GET /api/expenses/{id}` | Un gasto | `200` o `404` |
| ✅ | `POST /api/expenses` | Registra un gasto manual | `201` con `Expense` |
| ✅ | `PATCH /api/expenses/{id}` | Edita solo los campos enviados (`supplierId: null` quita el proveedor) | `200` con `Expense` |

Cuerpo de `POST /api/expenses`:

```json
{
  "categoryId": 3, "supplierId": 4, "total": 25.50, "description": "Pago de internet",
  "paymentMethod": "transferencia", "date": "2026-11-20T10:30:00-05:00", "receiptNumber": "001-001-000000123"
}
```

- Obligatorios: `categoryId`, `total` (mayor a 0), `description`, `paymentMethod`
  (`efectivo`, `tarjeta_debito`, `tarjeta_credito`, `transferencia`, `cheque`).
- `date` es opcional: sin ella se usa la hora actual; sin zona horaria se toma como hora de Ecuador.
- Categoría o proveedor que no son de la empresa → `422 CATEGORY_NOT_FOUND` / `422 SUPPLIER_NOT_FOUND`.

Objeto `Expense`:

```json
{
  "id": 12, "date": "2026-11-20T10:30:00-05:00", "categoryId": 3, "categoryName": "Servicios",
  "supplierId": 4, "supplierName": "Corporación Favorita", "supplierIdentification": "1790016919001",
  "total": 25.5, "description": "Pago de internet", "paymentMethod": "transferencia",
  "receiptNumber": "001-001-000000123", "status": "confirmado", "source": "manual"
}
```

- `source`: `manual` o `correo` (cuando lo lea el worker desde una factura recibida, RF-3.2).
- La base todavía no guarda el IVA del gasto por separado: el `ivaAmount` del frontend no tiene dónde
  guardarse (pendiente con Ariana).

## 12. Inventario: historial, entradas, salidas y ajustes

El stock de un producto **solo cambia junto con un movimiento** (ventas, entradas, salidas y ajustes), así el
historial siempre cuadra con el stock (DECISIONES 2.15). Registrar un movimiento **exige iniciar sesión**
(`403 USER_SESSION_REQUIRED`) porque guarda quién lo hizo.

| Estado | Método y ruta | Qué hace | Respuesta |
|---|---|---|---|
| ✅ | `GET /api/inventory/movements` | Historial paginado, el más reciente primero. Filtros: `productId`, `type` (`entrada`, `salida`, `ajuste`, `venta`), `from`, `to` (fechas de Ecuador) | `200` con `Page<InventoryMovement>` |
| ✅ | `GET /api/inventory/movements/{id}` | Un movimiento | `200` o `404` |
| ✅ | `POST /api/inventory/movements` | Entrada o salida manual (RF-4.3): `{ "productId", "type": "entrada" \| "salida", "quantity" (> 0), "reason" }` | `201` con `InventoryMovement` |
| ✅ | `POST /api/inventory/adjustments` | **Solo Administrador** (RF-4.8). Ajuste al conteo físico: `{ "productId", "newStock" (≥ 0), "reason" }`. Se envía el stock real, no la diferencia | `201` con `StockAdjustment` |

Errores: producto que no es de la empresa → `422 PRODUCT_NOT_FOUND`; salida mayor al stock →
`409 INSUFFICIENT_STOCK`; ajuste al mismo stock que ya tiene → `422 NO_STOCK_CHANGE`; motivo vacío → `422`.

Objeto `InventoryMovement` (igual que el modelo del frontend):

```json
{
  "id": 31, "productId": 5, "productName": "Café molido 250 g", "unit": "UNIDAD", "type": "salida",
  "quantity": -2.5, "resultingStock": 12.5, "reason": "Merma", "date": "2026-11-20T10:30:00-05:00",
  "createdBy": "Ana Torres"
}
```

- `quantity` lleva signo: **positiva si entra** al inventario, **negativa si sale** (ventas, salidas y ajustes a la baja).
- `resultingStock`: stock del producto justo después de ese movimiento.
- Para la pantalla de ajustes: `GET /api/inventory/movements?type=ajuste`.

Objeto `StockAdjustment` (respuesta del ajuste):

```json
{
  "id": 32, "productId": 5, "productName": "Café molido 250 g", "previousStock": 10, "newStock": 7,
  "quantityDelta": -3, "reason": "Conteo de fin de mes", "date": "2026-11-20T18:00:00-05:00",
  "createdBy": "Ana Torres"
}
```

- Las alertas de stock bajo (RF-4.6) ya existen: `GET /api/products?lowStock=true` (sección 4).

## 13. Dashboard financiero

**Solo el Administrador** (RF-5.5): cualquier otro rol recibe `403 FORBIDDEN`. Los indicadores se calculan **en vivo**
en cada consulta, así reflejan al instante cada venta, gasto o movimiento (RF-5.4).

| Estado | Método y ruta | Qué hace | Respuesta |
|---|---|---|---|
| ✅ | `GET /api/dashboard?from=&to=` | Indicadores del período (fechas `YYYY-MM-DD` de Ecuador). Sin fechas: el mes en curso hasta hoy. Máximo 366 días; `from` posterior a `to` → `422` | `200` con `DashboardSummary` |

Para RF-5.3 el frontend calcula el rango: hoy (`from = to = hoy`), semana, mes o personalizado.

```json
{
  "from": "2026-11-01", "to": "2026-11-20",
  "income": 2240.8, "expenses": 910, "profit": 1330.8,
  "salesCount": 125, "expensesCount": 9, "averageTicket": 17.93,
  "topProducts": [ { "productId": 1, "name": "Café en grano 500 g", "unitsSold": 98, "revenue": 833 } ],
  "dailySeries": [ { "date": "2026-11-01", "income": 74.5, "expenses": 0 } ],
  "expensesByCategory": [ { "categoryId": 6, "name": "Arriendo", "total": 450 } ],
  "inventory": {
    "activeProducts": 7, "lowStockCount": 2, "inventoryValue": 691.5,
    "lowStockProducts": [ { "productId": 5, "name": "Agua sin gas 500 ml", "unit": "UNIDAD", "currentStock": 6, "minStock": 12 } ]
  }
}
```

- `income`: total de las ventas **completadas** del período, **con IVA** (lo que entró a caja). Las anuladas no cuentan.
- `expenses`: gastos **confirmados**. `profit` = `income − expenses` (utilidad estimada, RF-5.2).
- `topProducts`: los 5 productos con más ingreso; `revenue` es el subtotal **sin IVA** de sus líneas.
- `dailySeries`: **un punto por cada día** del período, también los días en 0, listo para el gráfico.
- `inventory` es el estado **actual** (no depende del período): productos activos, cuántos tienen stock bajo,
  valor del inventario (stock × costo) y los 10 más críticos.
- Mismos nombres que `DashboardSummary` del frontend, más `expenses`, `expensesCount`, `expensesByCategory`,
  `inventory` y `dailySeries[].expenses`. Los ids pasan de `string` a `number`.
