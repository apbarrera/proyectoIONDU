# IONDU · Contrato de la API

> Qué datos viajan entre el frontend y el backend. Si cambia un endpoint, se actualiza aquí **antes** de programarlo.
> Estado de cada endpoint: ✅ disponible · 🚧 en construcción · ⏳ pendiente de una decisión.
> La documentación interactiva está en `/api/docs` (solo fuera de producción).

## 1. Reglas generales

- **Rutas relativas** bajo `/api/...` (Nginx las reenvía a la API). Nombres de rutas y del JSON en **inglés**, con
  el estilo del frontend (`camelCase`); la base de datos sigue en español y el backend traduce.
- **Empresa (multi-tenant):** cada petición trabaja solo con los datos de la empresa del usuario. Nunca se envía
  `id_empresa` en el cuerpo ni en la ruta.
  - **Ahora (solo desarrollo):** encabezado `X-Empresa-Id: <número>`. En producción ese encabezado se ignora y
    se responde `401`.
  - **Después (con Supabase Auth):** encabezado `Authorization: Bearer <token>`; la empresa sale del token.
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
| 404 | `NOT_FOUND` | El recurso no existe **o es de otra empresa** (no se revela cuál de las dos) |
| 409 | `PRODUCT_SKU_TAKEN`, … | Choca con un dato existente |
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
| `active` | boolean | ⏳ falta la columna `activo` | Se agregará cuando exista en la base (RF-4.1, desactivar) |

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
| ⏳ | Desactivar / reactivar | `PATCH` con `{ "active": false }` | Cuando exista la columna `activo` |

No hay `DELETE`: un producto con ventas o movimientos no se puede borrar sin romper el historial; se desactiva.

## 5. Cambios que implica en el frontend

1. `Product.id`: de `string` a `number`.
2. `category` (texto libre) pasa a ser `categoryId` (elegir de `GET /api/product-categories`) y `categoryName` (para mostrar).
3. `type`: valores según la decisión pendiente (hoy el frontend usa `simple`, `insumo`, `compuesto`).
4. Campos nuevos: `description`, `appliesVat`, `lowStock`.
5. El formulario de edición no debe cambiar `currentStock`; eso se hace desde Ajustes o Movimientos.
6. En `ProductsService`, reemplazar `simulateRequest(...)` por `HttpClient` contra estas rutas.
