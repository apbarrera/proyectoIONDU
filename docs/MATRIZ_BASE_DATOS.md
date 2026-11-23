# Matriz maestra de base de datos — IONDU

**Proyecto:** IONDU – Sistema Inteligente de Gestión Financiera para PyMEs
**Estado:** Auditoría estructural de 18 tablas
**Fuente de diseño:** Modelos SQLAlchemy actuales (`backend/app/models/`)
**Objetivo:** Documentar la estructura aprobada y los pendientes antes de generar el DDL definitivo.

---

## 1. Criterios generales

1. Los 18 modelos SQLAlchemy actuales son la fuente de verdad para el esquema.
2. La tabla antigua `usuario` no debe recuperarse: la autenticación utiliza Supabase Auth (`auth.users`) y la relación empresarial se gestiona mediante `usuario_empresa`.
3. El esquema debe incluir `usuario_empresa` y `secuencia_comprobante`.
4. Las claves foráneas entre entidades empresariales deben preservar el aislamiento por `id_empresa`.
5. Los certificados `.p12` y sus contraseñas se almacenan cifrados mediante envolventes completas AES-GCM.
6. Los campos temporales deben utilizar `TIMESTAMPTZ` cuando representan fechas y horas.
7. No se deben añadir restricciones CHECK basadas en valores supuestos. Primero deben verificarse los valores utilizados por los servicios.
8. La generación del esquema no autoriza su ejecución sobre las bases existentes.
9. La validación de instalación se realizará en una base de datos nueva, aislada y expresamente destinada a esa prueba.

## 2. Inventario de las 18 tablas

| N.º | Tabla | Responsabilidad |
|---:|---|---|
| 1 | `empresa` | Datos de la empresa y configuración de facturación electrónica. |
| 2 | `rol` | Catálogo de roles del sistema. |
| 3 | `usuario_empresa` | Membresías y roles de usuarios por empresa. |
| 4 | `categoria_gasto` | Clasificación de gastos por empresa. |
| 5 | `categoria_producto` | Clasificación de productos por empresa. |
| 6 | `cliente` | Clientes registrados por empresa. |
| 7 | `proveedor` | Proveedores registrados por empresa. |
| 8 | `producto` | Catálogo, precios e inventario de productos. |
| 9 | `venta` | Registro de ventas. |
| 10 | `detalle_venta` | Líneas de productos o conceptos libres de una venta. |
| 11 | `movimiento_inventario` | Historial de movimientos de inventario. |
| 12 | `gasto` | Registro de gastos empresariales. |
| 13 | `factura` | Emisión y autorización de comprobantes electrónicos. |
| 14 | `secuencia_comprobante` | Secuenciales por empresa y configuración de emisión. |
| 15 | `accion_ia` | Registro de acciones solicitadas al agente de IA. |
| 16 | `consumo_tokens` | Consumo y costo estimado de modelos de IA. |
| 17 | `recomendacion` | Recomendaciones financieras generadas. |
| 18 | `dashboard_financiero` | Indicadores financieros consolidados por período. |

## 3. Matriz estructural

### 3.1. Empresa y configuración

#### `empresa`

**Columnas principales:** `id_empresa`, `razon_social`, `nombre_comercial`, `ruc`, `actividad_economica`, `direccion`, `correo_electronico`, `datos_facturacion_electronica`, `certificado_p12_cifrado`, `certificado_password_cifrada`, `certificado_fecha_vencimiento`, `fecha_creacion`.

- PK: `id_empresa`.
- UNIQUE: `ruc`.
- CHECK: RUC de 13 dígitos.
- CHECK: certificado cifrado y contraseña cifrada deben estar ambos presentes o ambos ausentes.
- Cifrado: la envolvente completa contiene versión, nonce, contenido cifrado y etiqueta de autenticación.
- Decisión aprobada: no almacenar nonce y tag en columnas independientes.

#### `rol`

**Columnas principales:** `id_rol`, `nombre`, `descripcion`.

- PK: `id_rol`.
- UNIQUE: `nombre`.
- Roles utilizados: `Administrador` y `Operativo`.
- Pendiente: definir la estrategia de inserción inicial de roles.

#### `usuario_empresa`

**Columnas principales:** `id_usuario`, `id_empresa`, `id_rol`, `estado`, `nombre_visible`, `fecha_creacion`.

- PK compuesta: `(id_usuario, id_empresa)`.
- FK: `id_usuario` → `auth.users.id`, con eliminación en cascada.
- FK: `id_empresa` → `empresa.id_empresa`, con eliminación en cascada.
- FK: `id_rol` → `rol.id_rol`, con eliminación restringida.
- CHECK: `estado IN ('ACTIVO', 'INACTIVO', 'INVITADO')`.
- Índice: `idx_usuario_empresa_empresa(id_empresa)`.
- La identidad y contraseña del usuario pertenecen a Supabase Auth, no a una tabla propia.

#### `categoria_gasto`

**Columnas principales:** `id_categoria_gasto`, `id_empresa`, `nombre`, `origen`, `descripcion`.

- PK: `id_categoria_gasto`.
- FK: `id_empresa` → `empresa.id_empresa`, ON DELETE CASCADE.
- UNIQUE: `(id_empresa, id_categoria_gasto)`.
- UNIQUE: `(id_empresa, nombre)`.
- `origen` tiene valor predeterminado `PREDEFINIDA`.

#### `categoria_producto`

**Columnas principales:** `id_categoria_producto`, `id_empresa`, `nombre`, `descripcion`.

- PK: `id_categoria_producto`.
- FK: `id_empresa` → `empresa.id_empresa`, ON DELETE CASCADE.
- UNIQUE: `(id_empresa, id_categoria_producto)`.
- UNIQUE: `(id_empresa, nombre)`.

#### `secuencia_comprobante`

**Columnas principales:** `id_secuencia`, `id_empresa`, `establecimiento`, `punto_emision`, `tipo_comprobante`, `ultimo_secuencial`.

- PK: `id_secuencia`.
- FK: `id_empresa` → `empresa.id_empresa`, ON DELETE CASCADE.
- UNIQUE: `(id_empresa, establecimiento, punto_emision, tipo_comprobante)`.
- CHECK: establecimiento y punto de emisión de tres dígitos.
- CHECK: tipo de comprobante de dos dígitos.
- CHECK: secuencial entre 0 y 999999999.
- El servicio utiliza una operación atómica de incremento y retorno del secuencial.

### 3.2. Entidades comerciales

#### `cliente`

**Columnas principales:** `id_cliente`, `id_empresa`, `tipo_identificacion`, `identificacion`, `nombre_razon_social`, `direccion`, `telefono`, `correo_electronico`.

- PK: `id_cliente`.
- FK: `id_empresa` → `empresa.id_empresa`, ON DELETE CASCADE.
- UNIQUE: `(id_empresa, id_cliente)`.
- UNIQUE: `(id_empresa, tipo_identificacion, identificacion)`.
- Índice existente: `idx_cliente_empresa(id_empresa)`.
- Pendiente: confirmar catálogo definitivo de tipos de identificación.

#### `proveedor`

**Columnas principales:** `id_proveedor`, `id_empresa`, `ruc_identificacion`, `razon_social`, `telefono`, `correo_electronico`, `direccion`.

- PK: `id_proveedor`.
- FK: `id_empresa` → `empresa.id_empresa`, ON DELETE CASCADE.
- UNIQUE: `(id_empresa, id_proveedor)`.
- UNIQUE: `(id_empresa, ruc_identificacion)`.
- No se ha aprobado una restricción adicional que obligue a que toda identificación tenga formato de RUC.

#### `producto`

**Columnas principales:** `id_producto`, `id_empresa`, `id_categoria_producto`, `codigo_principal`, `nombre`, `descripcion`, `precio_compra`, `precio_venta`, `stock_actual`, `stock_minimo`, `unidad_medida`, `tipo`, `aplica_iva`, `codigo_porcentaje_iva`, `activo`.

- PK: `id_producto`.
- FK: `id_empresa` → `empresa.id_empresa`, ON DELETE CASCADE.
- FK compuesta: `(id_empresa, id_categoria_producto)` → `categoria_producto(id_empresa, id_categoria_producto)`, ON DELETE RESTRICT.
- UNIQUE: `(id_empresa, id_producto)`.
- Índice único funcional aprobado: `(id_empresa, lower(codigo_principal))`, nombre `producto_codigo_empresa_lower_uq`.
- Índices existentes: `idx_producto_categoria`, `idx_producto_empresa`.
- CHECK: precios y stock no negativos.
- CHECK: `codigo_porcentaje_iva IN ('0', '4', '5', '6', '7')`.
- Pendiente: decidir si se añade CHECK para `tipo IN ('VENTA', 'INSUMO', 'AMBOS')`.
- Pendiente: evaluar índices de consulta con evidencia del repositorio y, si procede, planes de ejecución.

#### `venta`

**Columnas principales:** `id_venta`, `id_empresa`, `id_usuario`, `id_cliente`, `fecha`, `subtotal`, `iva`, `monto_total`, `tipo_origen`, `metodo_pago`, `observacion`, `estado`.

- PK: `id_venta`.
- FK: `id_empresa` → `empresa.id_empresa`, ON DELETE CASCADE.
- FK compuesta: `(id_usuario, id_empresa)` → `usuario_empresa(id_usuario, id_empresa)`, ON DELETE RESTRICT.
- FK compuesta: `(id_empresa, id_cliente)` → `cliente(id_empresa, id_cliente)`, ON DELETE SET NULL sobre `id_cliente`.
- UNIQUE: `(id_empresa, id_venta)`.
- CHECK: subtotal, IVA y monto total no negativos.
- Índices aprobados:
  - `idx_venta_empresa_fecha_id(id_empresa, fecha DESC, id_venta DESC)`.
  - `idx_venta_empresa_cliente(id_empresa, id_cliente)`.
  - `idx_venta_usuario_empresa(id_usuario, id_empresa)`.
- Valores observados en el servicio: origen `MANUAL`; métodos de pago `EFECTIVO`, `TARJETA_DEBITO`, `TARJETA_CREDITO`, `TRANSFERENCIA`; estados `COMPLETADA`, `ANULADA`.
- Pendiente: aprobar CHECK para método de pago y estado después de cerrar las reglas de negocio y anulación.

#### `detalle_venta`

**Columnas principales:** `id_detalle_venta`, `id_empresa`, `id_venta`, `id_producto`, `descripcion_libre`, `cantidad`, `precio_unitario`, `descuento`, `codigo_porcentaje_iva`, `subtotal`.

- PK: `id_detalle_venta`.
- FK compuesta: `(id_empresa, id_venta)` → `venta(id_empresa, id_venta)`, ON DELETE CASCADE.
- FK compuesta: `(id_empresa, id_producto)` → `producto(id_empresa, id_producto)`, ON DELETE SET NULL sobre `id_producto`.
- CHECK: cantidad mayor que cero.
- CHECK: descuento, precio unitario y subtotal no negativos.
- CHECK: debe existir producto o descripción libre.
- CHECK: código IVA dentro de los valores admitidos.
- Índices aprobados:
  - `idx_detalle_venta_empresa_venta(id_empresa, id_venta, id_detalle_venta)`.
  - `idx_detalle_venta_empresa_producto(id_empresa, id_producto)`.
- Pendiente funcional: revisar que la descripción histórica guardada en `descripcion_libre` tenga prioridad al mostrar o emitir facturas, para no alterar ventas pasadas cuando cambie el nombre del producto.

#### `movimiento_inventario`

**Columnas principales:** `id_movimiento`, `id_empresa`, `id_producto`, `id_usuario`, `tipo_movimiento`, `cantidad`, `fecha`, `motivo`.

- PK: `id_movimiento`.
- FK compuesta: `(id_empresa, id_producto)` → `producto(id_empresa, id_producto)`, ON DELETE RESTRICT.
- FK compuesta: `(id_usuario, id_empresa)` → `usuario_empresa(id_usuario, id_empresa)`, ON DELETE RESTRICT.
- CHECK: `cantidad > 0`.
- Índices actuales:
  - `idx_movimiento_producto_fecha(id_producto, fecha DESC)`.
  - `idx_movimiento_usuario(id_usuario)`.
  - `idx_movimiento_empresa(id_empresa)`.
- Escritura localizada: el servicio de ventas registra `MOVIMIENTO_VENTA`.
- Decisión: no restringir todavía los tipos de movimiento; entradas, ajustes y devoluciones requieren definición funcional.
- Pendiente: revisar consultas de lectura antes de modificar índices.

#### `gasto`

**Columnas principales:** `id_gasto`, `id_empresa`, `id_categoria_gasto`, `id_usuario`, `id_proveedor`, `monto`, `fecha`, `numero_comprobante`, `message_id_correo`, `clave_acceso`, `concepto`, `metodo_pago`, `estado`.

- PK: `id_gasto`.
- FK: `id_empresa` → `empresa.id_empresa`, ON DELETE CASCADE.
- FK compuesta: `(id_empresa, id_categoria_gasto)` → `categoria_gasto(id_empresa, id_categoria_gasto)`, ON DELETE RESTRICT.
- FK compuesta: `(id_empresa, id_proveedor)` → `proveedor(id_empresa, id_proveedor)`, ON DELETE SET NULL sobre `id_proveedor`.
- FK compuesta: `(id_usuario, id_empresa)` → `usuario_empresa(id_usuario, id_empresa)`, ON DELETE RESTRICT.
- CHECK: `monto >= 0`.
- UNIQUE: `(id_empresa, clave_acceso)`.
- UNIQUE: `(id_empresa, message_id_correo)`.
- Índices: empresa/fecha descendente, proveedor y usuario.
- Los campos de clave de acceso y Message-ID permiten plantear idempotencia en importaciones.
- Pendiente: implementar y validar el servicio y el flujo de importación.

### 3.3. Facturación electrónica

#### `factura`

**Columnas principales:** `id_factura`, `id_empresa`, `id_venta`, `numero_comprobante`, `clave_acceso`, `estado_autorizacion`, `numero_autorizacion`, `fecha_autorizacion`, `mensajes_sri`, `intentos_envio`, `subtotal`, `impuestos`, `total`, `fecha_emision`, `xml_firmado`, `xml_autorizado`, `pdf_ride_path`.

- PK: `id_factura`.
- FK: `id_empresa` → `empresa.id_empresa`, ON DELETE CASCADE.
- FK compuesta: `(id_empresa, id_venta)` → `venta(id_empresa, id_venta)`, ON DELETE CASCADE.
- UNIQUE: `id_venta`.
- UNIQUE: `(id_empresa, numero_comprobante)`.
- UNIQUE: `clave_acceso`.
- CHECK: subtotal, impuestos, total e intentos de envío no negativos.
- CHECK: formato `numero_comprobante` = `NNN-NNN-NNNNNNNNN`.
- CHECK aprobado: `estado_autorizacion IN ('autorizada', 'rechazada', 'por_enviar', 'por_autorizar')`.
- Índice: `idx_factura_empresa_fecha(id_empresa, fecha_emision DESC)`.
- El servicio persiste la factura antes del envío al SRI y actualiza su estado con el resultado.
- Pendiente: implementar o verificar el proceso de reintentos y recuperación de emisiones pendientes.

### 3.4. Inteligencia artificial y análisis

#### `accion_ia`

**Columnas principales:** `id_accion_ia`, `id_empresa`, `id_usuario`, `tipo_accion`, `instruccion_recibida`, `payload_json`, `estado`, `fecha`.

- PK: `id_accion_ia`.
- FK: `id_empresa` → `empresa.id_empresa`, ON DELETE CASCADE.
- FK compuesta: `(id_usuario, id_empresa)` → `usuario_empresa(id_usuario, id_empresa)`, con eliminación que permite dejar `id_usuario` nulo.
- `id_usuario` nullable.
- Índice: empresa/fecha descendente.
- Pendiente: integración funcional y definición del ciclo de vida de acciones.

#### `consumo_tokens`

**Columnas principales:** `id_consumo_tokens`, `id_empresa`, `modelo_ia`, `tokens_prompt`, `tokens_completado`, `costo_estimado`, `fecha`.

- PK: `id_consumo_tokens`.
- FK: `id_empresa` → `empresa.id_empresa`, ON DELETE CASCADE.
- CHECK: tokens de entrada, tokens completados y costo estimado no negativos.
- Índice: empresa/fecha descendente.

#### `recomendacion`

**Columnas principales:** `id_recomendacion`, `id_empresa`, `tipo`, `descripcion`, `datos_utilizados`, `estado`, `fecha`.

- PK: `id_recomendacion`.
- FK: `id_empresa` → `empresa.id_empresa`, ON DELETE CASCADE.
- Índice: empresa/fecha descendente.
- Pendiente: definir catálogo de tipos y ciclo de vida de estados antes de restringirlos.

#### `dashboard_financiero`

**Columnas principales:** `id_dashboard`, `id_empresa`, `periodo`, `ingresos_totales`, `gastos_totales`, `utilidad_neta`, `ventas_registradas`, `gastos_por_categoria`, `estado_inventario`, `productos_stock_bajo`, `fecha_calculo`.

- PK: `id_dashboard`.
- FK: `id_empresa` → `empresa.id_empresa`, ON DELETE CASCADE.
- UNIQUE: `(id_empresa, periodo)`.
- CHECK: formato de período `YYYY-MM`.
- CHECK: contadores no negativos.
- La utilidad neta puede ser negativa.
- Pendiente: integración y actualización de indicadores.

## 4. Cambios aprobados en los modelos

Los siguientes cambios ya fueron aplicados en el código y comprobados mediante metadata SQLAlchemy:

| Archivo | Cambio aprobado |
|---|---|
| `empresa.py` | CHECK de presencia conjunta del certificado cifrado y contraseña cifrada. |
| `producto.py` | Índice único funcional por empresa y `lower(codigo_principal)`. |
| `venta.py` | Índices compuestos por empresa, fecha, cliente y usuario. |
| `detalle_venta.py` | Índices compuestos por empresa, venta y producto. |
| `factura.py` | CHECK de los cuatro estados de autorización. |

**Importante:** estas comprobaciones validan la metadata del modelo, no demuestran que una base de datos existente ya tenga físicamente los cambios. Para eso se necesitarán migraciones y una instalación de prueba aislada.

## 5. Pendientes de diseño y validación

| Prioridad | Pendiente | Motivo |
|---|---|---|
| Alta | Crear un DDL completo a partir de los 18 modelos | El `database/schema.sql` histórico está desactualizado. |
| Alta | Crear una migración inicial coherente | Las migraciones actuales son incrementales y no crean las 18 tablas desde cero. |
| Alta | Auditar instalación limpia y sus precondiciones | El instalador actual espera 17 tablas y valida un nombre de base distinto del objetivo configurado. |
| Alta | Separar tablas, funciones/triggers, RLS y permisos | `create_all` no instala por sí solo toda la infraestructura. |
| Alta | Validar RLS con un rol que no sea superusuario ni tenga BYPASSRLS | Las pruebas actuales advierten que el usuario de pruebas puede tener privilegios que impiden demostrar RLS. |
| Media | Definir CHECK de métodos de pago y estados de venta | Valores observados en el servicio; falta cerrar reglas de negocio. |
| Media | Definir tipos de movimiento de inventario | Actualmente se localizó la escritura `VENTA`; faltan otros movimientos previstos. |
| Media | Revisar persistencia histórica de descripción de venta | Evitar que cambios de nombre de producto alteren registros pasados. |
| Media | Confirmar tipos de identificación de clientes | Evitar restricciones incompatibles con identificaciones admitidas. |
| Media | Completar servicios de gastos, acciones IA, recomendaciones y dashboard | El modelo no equivale a integración funcional. |
| Media | Revisar reintentos de facturación electrónica | `intentos_envio` existe, pero el flujo de recuperación debe verificarse. |

## 6. Infraestructura que debe documentarse por separado

El DDL definitivo no debe mezclar responsabilidades. Se organizará en estos bloques:

1. **Esquema relacional:** tablas, columnas, claves primarias, claves foráneas, UNIQUE, CHECK e índices.
2. **Funciones y triggers:** validación de membresías y consistencia empresarial.
3. **Autenticación:** referencias a `auth.users` de Supabase; no crear una tabla de usuarios propia.
4. **Seguridad RLS:** políticas por empresa y rol, permisos y pruebas con un rol no privilegiado.
5. **Datos iniciales:** roles y otros catálogos que se decidan como semillas.

## 7. Protección de bases de datos durante la validación

- No ejecutar pruebas de instalación ni scripts destructivos sobre `iondu`.
- No utilizar `iondu_test` como base de instalación o migración: se reserva para pruebas automatizadas.
- Crear y auditar una base de datos independiente para instalación limpia.
- No ejecutar `alembic upgrade`, `downgrade`, `stamp` ni instaladores hasta verificar el destino y aprobar el procedimiento.
- No modificar ni reemplazar archivos locales del usuario sin autorización.
- Mantener los secretos fuera del documento y de los logs.

---

**Estado del documento:** matriz de referencia elaborada a partir de la auditoría de los 18 modelos. Los pendientes identificados deben resolverse o quedar explícitamente documentados antes de declarar definitivo el esquema de producción.

---

## 8. Seguridad PostgreSQL: privilegios mínimos y RLS

**Estado:** auditoría de privilegios y RLS comprobada en la base aislada `iondu_fresh_install_test_v2`. La implementación y validación de producción siguen pendientes.

### 8.1. Principios

1. `iondu_app` es el rol de ejecución de la API: `LOGIN`, `NOSUPERUSER` y `NOBYPASSRLS`.
2. `iondu_app` no es propietario de las tablas.
3. Las migraciones utilizan credenciales administrativas separadas de `DATABASE_URL`.
4. Los permisos SQL no sustituyen las políticas RLS ni la autorización de la aplicación.
5. Los filtros explícitos `id_empresa` se mantienen en los repositorios.
6. No se conceden permisos anticipados a funcionalidades que todavía no tienen operaciones implementadas.
7. Los resultados de la base aislada no se extrapolan automáticamente a otras bases de datos.

### 8.2. Matriz de privilegios del runtime

| Tabla | SELECT | INSERT | UPDATE | DELETE | Alcance |
|---|---|---|---|---|---|
| empresa | Sí | No | Columnas específicas | No | Lectura empresarial y actualización de certificado |
| usuario_empresa | Sí | No | No | No | Consulta de membresías |
| rol | Sí | No | No | No | Catálogo de roles |
| cliente | Sí | Sí | Columnas específicas | No | Operaciones actuales de clientes |
| categoria_producto | Sí | Sí | No | No | Consulta y creación |
| producto | Sí | Sí | Columnas específicas | No | Catálogo y actualización de inventario |
| venta | Sí | Sí | No | No | Registro y consulta de ventas |
| detalle_venta | Sí | Sí | No | No | Líneas de venta |
| movimiento_inventario | No | Sí | No | No | Registro de movimientos desde ventas |
| factura | Sí | Sí | Columnas específicas | No | Emisión y generación de RIDE |
| secuencia_comprobante | Por columnas | Por columnas | Por columnas | No | Reserva atómica de secuenciales |
| gasto | No | No | No | No | Sin operaciones de runtime identificadas |
| proveedor | No | No | No | No | Sin operaciones de runtime identificadas |
| categoria_gasto | No | No | No | No | Sin operaciones de runtime identificadas |
| dashboard_financiero | No | No | No | No | Sin operaciones de runtime identificadas |
| accion_ia | No | No | No | No | Sin operaciones de runtime identificadas |
| recomendacion | No | No | No | No | Sin operaciones de runtime identificadas |
| consumo_tokens | No | No | No | No | Sin operaciones de runtime identificadas |

**Precisión sobre permisos por columna:**

- `empresa`: UPDATE limitado a `certificado_p12_cifrado`, `certificado_password_cifrada` y `certificado_fecha_vencimiento`.
- `cliente`: UPDATE limitado a `tipo_identificacion`, `identificacion`, `nombre_razon_social`, `direccion`, `telefono` y `correo_electronico`.
- `producto`: UPDATE limitado a las columnas de producto autorizadas, incluido `stock_actual`.
- `factura`, API: UPDATE de `pdf_ride_path`.
- `factura`, worker: UPDATE de `estado_autorizacion`, `numero_autorizacion`, `fecha_autorizacion`, `mensajes_sri`, `intentos_envio`, `xml_autorizado` y `pdf_ride_path`.
- `secuencia_comprobante`: permisos por columna sobre `id_empresa`, `establecimiento`, `punto_emision`, `tipo_comprobante` y `ultimo_secuencial`. El UPSERT utiliza INSERT, UPDATE y RETURNING.
- `venta`: no se encontró ninguna actualización de la entidad en el flujo actual. `SELECT FOR UPDATE` no justifica por sí solo conceder UPDATE.
- `movimiento_inventario`: no se encontraron consultas de lectura en el backend actual. Solo se justifica INSERT.

Las siete tablas sin operaciones identificadas conservan RLS, pero no tienen permisos de tabla concedidos a `iondu_app` en la base aislada auditada. Su futura habilitación requiere implementar y probar primero los servicios correspondientes.

### 8.3. Permisos generales

En la configuración auditada se comprobaron las siguientes restricciones:

| Recurso | Criterio |
|---|---|
| Base de datos | CONNECT para el runtime |
| Esquema `public` | USAGE |
| Esquema `public` | Sin CREATE para el runtime |
| Esquema `auth` | Sin acceso directo a `auth.users` |
| Roles PostgreSQL | Sin privilegios administrativos |
| Tablas | Sin propiedad por `iondu_app` |
| RLS | Sin BYPASSRLS |

Los resultados deben volver a comprobarse en el destino definitivo antes de producción.

### 8.4. Secuencias

Se identificaron 17 secuencias asociadas a columnas Identity o Serial en la base aislada.

Resultados de privilegios:

- `factura_id_factura_seq`: `iondu_app` tiene USAGE.
- `secuencia_comprobante_id_secuencia_seq`: `iondu_app` tiene USAGE.
- Las otras 15 secuencias no tienen USAGE concedido explícitamente a `iondu_app`.
- `iondu_worker` no tiene USAGE sobre las secuencias auditadas.
- No se identificaron privilegios SELECT o UPDATE de secuencia para los roles runtime.

**Pruebas realizadas:**

1. INSERT de venta con generación automática de ID como `iondu_app`, sin USAGE sobre su secuencia: aprobado.
2. INSERT de factura con generación automática de ID como `iondu_app`, con el USAGE actualmente concedido: aprobado.
3. UPSERT de `secuencia_comprobante`, incluyendo RETURNING e incremento consecutivo de 1 a 2, sin USAGE durante la transacción de prueba: aprobado.

Las pruebas sintéticas se ejecutaron en `iondu_fresh_install_test_v2` y sus registros de prueba fueron revertidos mediante ROLLBACK.

**Pendiente:** evaluar la concesión permanente de USAGE de `secuencia_comprobante`, que no resultó necesaria en la prueba. No revocar permisos sin una autorización específica y una comprobación adicional.

No conceder privilegios indiscriminados sobre todas las secuencias.

### 8.5. Privilegios predeterminados

En `iondu_fresh_install_test_v2` no se encontraron privilegios predeterminados personalizados en `pg_default_acl`.

Este resultado no demuestra el estado de los privilegios predeterminados de otras bases de datos.

**Pendiente:**

1. Auditar los privilegios predeterminados en el destino definitivo.
2. Revisar el propietario que crea los objetos durante las migraciones.
3. Definir privilegios mínimos para objetos nuevos.
4. Probar que las migraciones futuras mantienen el modelo de privilegios.

No ejecutar cambios de privilegios predeterminados hasta preparar y aprobar la estrategia de migraciones.

### 8.6. Estrategia RLS

Tablas empresariales sujetas a aislamiento:

- `categoria_gasto`
- `categoria_producto`
- `cliente`
- `proveedor`
- `producto`
- `venta`
- `detalle_venta`
- `movimiento_inventario`
- `gasto`
- `factura`
- `secuencia_comprobante`
- `accion_ia`
- `consumo_tokens`
- `recomendacion`
- `dashboard_financiero`

Tablas especiales:

- `usuario_empresa`: permite consultar las membresías propias.
- `empresa`: limita la consulta a empresas con membresía activa.
- `rol`: catálogo global de lectura.

**Resultado comprobado en `iondu_fresh_install_test_v2`:**

- 18 de 18 tablas públicas con RLS habilitado y forzado.
- 14 políticas identificadas.
- Políticas específicas para membresías, empresa y rol.
- Políticas empresariales para las tablas de negocio.
- Política de acceso del worker a facturas y lectura de empresa.

Las políticas verificadas incluyen:

- `usuario_empresa_app_select`
- `rol_app_select`
- `empresa_app_select`
- `empresa_app_update`
- `factura_worker_access`
- `empresa_worker_select`

La autorización empresarial requiere una membresía con estado `ACTIVO`.

**Identidad y contexto:** los valores `app.current_user_id` y `app.current_empresa_id` son configurables por una conexión SQL. No constituyen por sí solos una identidad autenticada. La vinculación entre JWT validado y contexto RLS debe mantenerse como requisito de seguridad.

Si se utilizan funciones `SECURITY DEFINER`, deberán contar con `search_path` fijo, propietario restringido y privilegios EXECUTE mínimos.

### 8.6.1. Acceso transversal del worker

El worker es un servicio técnico de confianza que procesa una cola global de
facturas electrónicas pertenecientes a distintas empresas. Por este motivo,
su acceso a los registros de `factura` no se limita al contexto de un ?nico
`id_empresa`.

- `factura_worker_access` permite al rol `iondu_worker` operar sobre las
  facturas que debe procesar, sin filtro por empresa (`USING (true)` y
  `WITH CHECK (true)`).
- `empresa_worker_select` permite consultar los datos de configuración
  necesarios para procesar cada factura.
- `iondu_worker` es un rol `LOGIN`, `NOSUPERUSER` y `NOBYPASSRLS`.
  El acceso transversal se concede mediante sus políticas RLS, no mediante
  la omisión de RLS.
- Los permisos de columnas del worker están restringidos. En `factura`,
  sus actualizaciones se limitan a los campos requeridos para registrar
  el resultado del procesamiento; no tiene permisos USAGE sobre las
  secuencias auditadas.
- La API mantiene un modelo distinto: el acceso de sus usuarios se valida
  mediante JWT, pertenencia activa, empresa seleccionada y contexto RLS.

**Implicación de seguridad:** `iondu_worker` es una identidad técnica con
confianza transversal entre empresas. Sus credenciales, conexión y ejecución
deben protegerse como componentes privilegiados del sistema. No debe
reutilizarse para peticiones de usuarios ni exponerse al frontend.

**Alcance de la comprobación:** la definición de las políticas, los atributos
del rol y los permisos de columnas se comprobaron en
`iondu_fresh_install_test_v2`. Las pruebas automatizadas de lógica y sesión
del worker aprobaron (20 pruebas; 2 pruebas de bloqueo con fixture de base
de datos fueron excluidas). La validación integral de las operaciones SQL
del worker con el rol real `iondu_worker` y la comprobación en el entorno
de despliegue permanecen pendientes.

### 8.7. Estado de la auditoría de seguridad

| Comprobación | Resultado |
|---|---|
| Login real de `iondu_app` | Validado |
| `NOSUPERUSER` y `NOBYPASSRLS` | Validados |
| Sin CREATE en `public` | Validado |
| Sin acceso directo a `auth.users` | Validado |
| RLS habilitado y forzado | 18/18 en base aislada |
| Políticas RLS | 14 identificadas en base aislada |
| ACL de tablas | Auditadas |
| Permisos por columna | Auditados para las tablas con permisos específicos |
| Generación de ID de venta sin USAGE | Probada |
| Generación de ID de factura con USAGE | Probada |
| UPSERT de secuenciales sin USAGE | Probado |
| Privilegios predeterminados de la base aislada | Sin ACL personalizadas |
| Privilegios predeterminados del destino definitivo | Pendiente |
| Vinculación segura JWT-contexto RLS | Pendiente de validación integral |
| Pruebas de aislamiento con dos empresas | Pendiente de aceptación integral |
| Validación final en entorno de despliegue | Pendiente |

### 8.8. Criterios de aceptación

La implementación no se considerará terminada hasta demostrar que:

1. `iondu_app` ejecuta las operaciones legítimas del backend.
2. No puede realizar operaciones no concedidas.
3. Un usuario no puede leer ni modificar registros de otra empresa.
4. No puede acceder a datos empresariales sin contexto autorizado.
5. Las membresías inactivas no permiten acceso.
6. El contexto se conserva correctamente con transacciones y reutilización de conexiones.
7. Las pruebas se ejecutan en una base de seguridad independiente y nunca sobre una base activa.
8. Las pruebas de regresión existentes siguen aprobadas.
9. Las migraciones futuras conservan los privilegios mínimos.

### 8.9. Orden de implementación pendiente

1. Separar configuración de conexión runtime y migraciones.
2. Definir y validar identidad segura y contexto de autorización.
3. Auditar y corregir privilegios predeterminados del destino definitivo.
4. Aplicar y verificar privilegios mínimos por tabla, columna y secuencia.
5. Validar funciones auxiliares y políticas RLS.
6. Ejecutar pruebas con `iondu_app` y `iondu_worker` en una base independiente.
7. Ejecutar regresión y documentar resultados.
8. Validar el procedimiento de despliegue sin intervenir bases activas.

---

**Estado de la sección:** auditoría de privilegios y RLS realizada en la base aislada. No equivale todavía a una certificación de seguridad del entorno de producción.
