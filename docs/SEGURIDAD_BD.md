## Autenticación: RLS en `usuario` y `sesion_refresh` — 26/11/2026

> Migraciones `e1f3a5b7c902_dueno_de_funciones_security_definer` y
> `d6a8c0e2f417_proteger_usuarios_y_sesiones`. Validadas en PostgreSQL 17 desechable (instalación limpia
> de punta a punta, subida, `alembic check`, bajada y nueva subida). **No aplicadas en la base `iondu`**:
> requieren revisión, respaldo reciente y autorización expresa (procedimiento en el punto 6).

### 1. Problema

Las dos tablas no tenían RLS. `iondu_app` podía leer todos los usuarios con su hash de contraseña,
todas las sesiones, y cambiar contraseñas o revocar sesiones de cualquiera. El login y la renovación
ocurren antes de conocer al usuario y a la empresa, así que no sirve una política por empresa.

### 2. Alternativas evaluadas

| | Funciones `SECURITY DEFINER` llamadas por `iondu_app` | Rol `iondu_auth` con conexión propia (**elegida**) |
|---|---|---|
| Hash de la contraseña | El login lo verifica en Python (argon2): la función tendría que devolverlo a `iondu_app`, y cualquier consulta de `iondu_app` (por ejemplo, una inyección SQL en otro endpoint) podría pedirlo por correo | Solo lo lee `iondu_auth`, cuya conexión usa únicamente el servicio de autenticación |
| Bloqueo de filas y atomicidad | Hay que reescribir la lógica en PL/pgSQL | El código actual (`FOR UPDATE`, una transacción) no cambia |
| Costo | Ninguna variable nueva | `AUTH_DATABASE_URL` y un pool pequeño en la API |

### 3. Diseño aplicado

| Rol | `usuario` | `sesion_refresh` | Otros |
|---|---|---|---|
| `iondu_app` | `SELECT (id, email)` con RLS: su propio usuario y los miembros de la empresa del contexto que el RLS de `usuario_empresa` le muestre (el Administrador, todos; el Operativo, solo a sí mismo) | Nada | — |
| `iondu_auth` | `SELECT` de sus 7 columnas, `INSERT (id, email, password_hash)`, `UPDATE (password_hash, intentos_fallidos, bloqueado_hasta)` | `SELECT`, `INSERT` (solo de cuentas activas, por política), `UPDATE (rotada_en, revocada_en)`, `DELETE` (limpieza de vencidas) | Ninguna otra tabla. Solo `EXECUTE` de `auth_puede_restablecer` |
| `iondu_worker`, `PUBLIC` | Nada | Nada | Nada |
| `iondu_funciones` (`NOLOGIN`) | — | — | Dueño de las funciones `SECURITY DEFINER`. Solo `SELECT (id_usuario, id_empresa, id_rol, estado)` de `usuario_empresa` y `SELECT (id_rol, nombre)` de `rol`, con políticas exclusivas |

RLS habilitado y **forzado** en `usuario` y `sesion_refresh`. Ningún rol es superusuario ni tiene
`BYPASSRLS`; `iondu_app` e `iondu_auth` no comparten membresía.

`auth_puede_restablecer(usuario, empresa)` responde solo `OK`, `NO_PERTENECE` u `OTRA_EMPRESA`: así
`iondu_auth` impide que un Administrador restablezca la contraseña de quien trabaja en otra empresa sin
poder leer `usuario_empresa`. La ejecuta solo `iondu_auth`.

Código: `get_auth_db` (`app/db/session.py`) da la sesión de `iondu_auth`. La usan el login, la
renovación, el cierre, el cambio de contraseña (con el id del token verificado, nunca uno del
cliente) y `app/services/cuentas.py` (crear o reutilizar una cuenta, restablecer una contraseña).
`UsuarioService` comprueba con `iondu_app` y el RLS que quien llama es Administrador y que el usuario
pertenece a su empresa; `CuentasAuth` lo vuelve a comprobar en la misma transacción que escribe.

### 4. Corrección: el dueño de las funciones `SECURITY DEFINER`

`app_es_admin_de` y `app_usuario_en_otras_empresas` consultan `usuario_empresa` y `rol` (RLS forzado,
políticas solo para `iondu_app`). Una función `SECURITY DEFINER` se ejecuta como su dueño. Comprobado en
PostgreSQL 17: si el dueño es `iondu_migrator` (sin `BYPASSRLS`, con permisos sobre las tablas como en la
base local), **devuelven siempre `false`**; si además no tuviera `SELECT`, fallarían con *permission
denied*. Lo que se rompe:

| Consumidor | Efecto con las funciones rotas |
|---|---|
| Políticas `usuario_empresa_app_admin_select/insert/update` | El Administrador solo se ve a sí mismo: no lista, no agrega ni edita usuarios de su empresa |
| Política `auditoria_app_select` | El Administrador no ve la auditoría |
| `UsuarioService._en_otras_empresas` | Diría que nadie trabaja en otra empresa |
| `usuario_app_select` (nueva) | El listado de usuarios no mostraría sus correos |

La migración `e1f3a5b7c902` las pasa a `iondu_funciones`, sin dar `BYPASSRLS` a nadie. El cambio de
dueño exige ejecutar la migración como administrador (en local, `iondu`, como el resto).

### 5. Pruebas (`backend/tests/postgres_auth/`, 79 con roles reales)

Login correcto e incorrecto, bloqueo, usuario inactivo, renovación, reutilización de un token rotado,
cierre, cambio y restablecimiento de contraseña (revocan todas las sesiones), cuentas de otra empresa o de
varias, creación de usuarios; operaciones del Administrador (listar, editar rol y estado, no
modificarse a sí mismo, no tocar otra empresa, auditoría); reproducción del fallo de las funciones y su
corrección; privilegios de `iondu_app`, `iondu_auth`, `iondu_worker` e `iondu_funciones`; quién ejecuta
cada función (nunca `PUBLIC`); RLS de negocio intacto; las migraciones suben y bajan sin cambiar las
políticas existentes; los roles se crean con los atributos exigidos y un rol preexistente con
un atributo obligatorio incumplido detiene la migración sin aplicar nada (6 atributos en
`iondu_funciones`, 5 en `iondu_auth`, que sí puede tener LOGIN); bajar y volver a subir funciona con
`iondu_auth` en uso; la bajada restaura una foto completa de permisos, dueños, RLS, políticas y funciones
(con el dueño por defecto y con las funciones a nombre de `iondu_migrator`).

`scripts/configurar_roles_locales.py` solo ejecuta `ALTER ROLE … LOGIN PASSWORD`: exige que cada URL use su
rol (`DATABASE_URL` → `iondu_app`, `AUTH_DATABASE_URL` → `iondu_auth`, `WORKER_DATABASE_URL` →
`iondu_worker`), contraseñas de 12 caracteres o más, distintas entre sí y de la del administrador, sin
marcadores del `.env.example`; no habilita un rol con privilegios de administrador y exige que
`iondu_funciones` no tenga LOGIN.

### 6. Orden de instalación

Instalación nueva y base existente siguen el mismo orden (el README lo describe con Docker):

1. Base existente: respaldo, `docker exec proyectoiondu-db-1 pg_dump -U iondu -d iondu -Fc > iondu_antes_auth.dump`.
2. `.env`: `AUTH_DATABASE_URL=postgresql+psycopg://iondu_auth:<clave>@db:5432/iondu`. Va antes del paso 3 porque
   Compose la exige para el servicio `api`.
3. `docker compose run --rm --no-deps api alembic upgrade head` (como `iondu`): crea `iondu_auth` e
   `iondu_funciones` con `NOLOGIN NOSUPERUSER NOBYPASSRLS NOCREATEROLE NOCREATEDB NOINHERIT`, corrige el
   dueño de las funciones y protege las tablas. **Antes de conceder nada valida los atributos** de los
   roles que ya existan, sin cambiarlos nunca:

   | Rol | Obligatorio | LOGIN |
   |---|---|---|
   | `iondu_funciones` | `NOSUPERUSER NOBYPASSRLS NOCREATEROLE NOCREATEDB NOINHERIT` | Prohibido (`NOLOGIN`) |
   | `iondu_auth` | `NOSUPERUSER NOBYPASSRLS NOCREATEROLE NOCREATEDB NOINHERIT` | Permitido: la API se conecta con él |

   Si un atributo obligatorio no se cumple, la migración se detiene con un error que lo nombra y no
   aplica nada.
4. `docker compose run --rm --no-deps api python -m scripts.configurar_roles_locales`: LOGIN de `iondu_app`,
   `iondu_auth` e `iondu_worker` con las claves de `.env`. `iondu_funciones` nunca tiene LOGIN.
5. `docker compose up -d --build` y probar: login, renovación, cambio de contraseña, gestión de usuarios, auditoría.
   Después de una bajada, la migración se puede volver a ejecutar sin tocar `iondu_auth`: conserva su
   LOGIN y su contraseña.
6. Vuelta atrás (base existente): `alembic downgrade c4e6a8b0d215`. Restaura exactamente los permisos (de
   tabla y de columna), las políticas, el RLS y el dueño anterior de cada función, que la subida guarda en
   su comentario (`[iondu:dueno_anterior=…]`). Solo quedan los roles `iondu_auth` e `iondu_funciones`, sin
   ningún permiso ni objeto. Si hiciera falta, el respaldo.

`scripts/crear_usuario.py` y `scripts/cargar_datos_demo.py` (siembra) usan `MIGRATION_DATABASE_URL`: con el
RLS forzado debe ser el administrador (`iondu`).

---

## Auditoría actualizada - 2026-11-24

### 1. Estado de migraciones

Se validó la ejecución completa de Alembic desde una base de datos aislada y vacía:

- Base de validación: `iondu_migration_test`.
- Revisión final: `b72e91c4a630` (head).
- Migraciones ejecutadas correctamente: 6 de 6.
- La base operativa `iondu` y la base de pruebas `iondu_test` no fueron modificadas durante esta validación.

### 2. Comparación entre `iondu` e `iondu_migration_test`

Se compararon las definiciones estructurales de ambas bases:

| Elemento | `iondu` | `iondu_migration_test` | Diferencias |
|---|---:|---:|---:|
| Tablas públicas | 19 | 19 | 0 |
| Columnas y definiciones | Coincidentes | Coincidentes | 0 |
| Restricciones | 103 | 103 | 0 |
| Índices | 59 | 59 | 0 |
| Tablas con RLS habilitado y forzado | 19 | 19 | 0 |
| Políticas RLS | 22 | 22 | 0 |

**Resultado:** las definiciones comparadas coinciden entre la base operativa y la base reconstruida desde cero mediante las migraciones.

Esta comparación no representa una equivalencia completa de todos los objetos o datos de PostgreSQL. No se compararon datos, permisos efectivos de todos los roles, funciones, triggers, secuencias ni extensiones.

### 3. Pruebas y permisos verificados

- Suite del backend: 389 pruebas aprobadas.
- Las pruebas se ejecutaron sobre `iondu_test` mediante el rol restringido `iondu_test_runner`.
- Se verificaron los permisos del rol `iondu_worker` para consultar y actualizar únicamente los campos autorizados de facturas, junto con su política RLS.
- `dashboard_financiero` todavía no está integrado en los servicios del backend ni en el frontend. No se concedieron permisos adicionales por anticipado.

### 4. Pendientes

Esta auditoría no certifica que el sistema esté listo para producción. Continúan pendientes:

1. Validación de autenticación real con Supabase, JWT, membresías y aislamiento entre empresas.
2. Integración y pruebas funcionales del frontend con el backend.
3. Pruebas de emisión electrónica real en el entorno de certificación del SRI.
4. Validación de despliegue, configuración de producción y CI/CD.
5. Configuración y comprobación de copias de seguridad, restauración y monitoreo.
6. Integración del dashboard financiero y sus permisos cuando se implemente.

> **Nota de actualización:** esta sección contiene los resultados vigentes de la auditoría al 24 de noviembre de 2026. Las cifras anteriores del documento corresponden a revisiones históricas y no deben interpretarse como el estado actual.

---
# IONDU · Auditoría y decisiones de seguridad de la base de datos

> Registro de la auditoría de `iondu_prueba`, realizada el 25 de octubre de 2026. Se distinguen los hallazgos comprobados, las decisiones acordadas y los puntos pendientes. La auditoría fue de solo lectura; no se modificaron tablas, políticas, funciones ni privilegios durante esta revisión.

## 1. Alcance y límites

Se inspeccionaron las políticas RLS, los privilegios efectivos de tablas y secuencias, las columnas `IDENTITY`, los permisos de funciones, los atributos de roles y las membresías entre roles.

Los resultados describen la base local `iondu_prueba`; no demuestran qué roles o configuración existen en el proyecto remoto de Supabase. Tampoco constituyen una prueba completa de aislamiento multiempresa.

## 2. Hallazgos comprobados

### 2.1 Seguridad a nivel de fila (RLS)

- RLS está habilitado en 16 de las 17 tablas públicas inspeccionadas. La tabla `rol` tiene RLS deshabilitado.
- Las políticas encontradas se aplican al rol `PUBLIC`. Esto no concede por sí solo privilegios SQL sobre las tablas: también se requieren los privilegios correspondientes.
- La mayoría de las políticas de negocio comprueba que el usuario tenga una membresía `usuario_empresa` activa para la empresa del registro.
- `dashboard_financiero` exige una membresía activa con el rol `Administrador`.
- `empresa` tiene políticas de lectura para miembros activos y actualización para administradores activos.
- `usuario_empresa` tiene una política `SELECT` limitada a la propia identidad mediante `auth.uid()`.
- Las políticas RLS no sustituyen los controles de permisos SQL, las reglas de transición de estados ni la protección del historial.

### 2.2 Roles y privilegios de tablas

- `postgres` tiene privilegios de lectura y escritura, incluidos `DELETE` y `TRUNCATE`, en las 17 tablas inspeccionadas. Es superusuario y puede omitir RLS.
- `iondu_rls_test` solo tiene `SELECT` efectivo sobre `dashboard_financiero`, `rol` y `usuario_empresa`. No tiene privilegios efectivos de escritura en las tablas auditadas.
- `iondu_rls_test` tiene `rolcanlogin = false`, `rolsuper = false` y `rolbypassrls = false`. No es una cuenta funcional para probar el acceso normal de la aplicación.
- Entre los roles consultados, la base local devolvió `postgres` e `iondu_rls_test`; no aparecieron `anon`, `authenticated` ni `service_role`. Esto no permite inferir la configuración de Supabase remoto.

### 2.3 Secuencias e identidades

- Se encontraron 16 secuencias públicas, todas propiedad de `postgres`.
- Las 16 columnas de identificación auditadas usan `GENERATED BY DEFAULT AS IDENTITY`.
- `postgres` tiene privilegios efectivos `USAGE`, `SELECT` y `UPDATE` sobre las secuencias.
- `iondu_rls_test` no tiene esos privilegios efectivos. Concederle únicamente `INSERT` sobre una tabla no resolvería por sí solo todos los permisos necesarios para insertar registros con identificadores generados.

### 2.4 Funciones y triggers

Se inspeccionaron estas funciones:

- `validar_membresia_activa()`: comprueba que el usuario tenga una membresía activa para la empresa. Se utiliza en triggers de `venta`, `gasto` y `accion_ia`.
- `validar_detalle_venta_empresa()`: comprueba que exista la venta y que el producto asociado, si existe, pertenezca a la misma empresa.
- `validar_movimiento_inventario_empresa()`: comprueba que exista el producto y que el usuario tenga una membresía activa en su empresa.

Las tres funciones pertenecen a `postgres`, utilizan `SECURITY INVOKER` y tienen `EXECUTE` concedido a `PUBLIC`. Su ejecución normal está asociada a los triggers correspondientes.

No se identificó un trigger que actualice automáticamente `producto.stock_actual` entre los triggers inspeccionados.

### 2.5 Membresías entre roles

La consulta de `pg_auth_members` no devolvió concesiones de roles que involucren a `postgres` o `iondu_rls_test según el filtro utilizado.

## 3. Decisiones acordadas

### 3.1 No usar `postgres` como credencial ordinaria de la aplicación

**Decisión:** el backend no utilizará el rol superusuario `postgres` como identidad ordinaria de conexión en producción.

**Motivo:** al poder omitir RLS y disponer de privilegios administrativos, su uso reduciría la eficacia de la defensa en profundidad y aumentaría el impacto de una vulnerabilidad.

La identidad de conexión y sus privilegios exactos se definirán al configurar Supabase.

### 3.2 No convertir `iondu_rls_test` en el rol definitivo de aplicación

**Decisión:** mantenerlo como rol de prueba limitado hasta diseñar un entorno reproducible. No conceder permisos improvisados solo para hacer pasar pruebas.

**Motivo:** no puede iniciar sesión, solo lee tres tablas y no puede utilizar las secuencias. Tampoco representa por sí mismo el modelo de autenticación de Supabase.

No se modificó este rol durante la auditoría.

### 3.3 Defensa en profundidad para el aislamiento multiempresa

**Decisiones:**

- Cada endpoint y consulta del backend debe filtrar por `id_empresa`.
- El backend debe validar el JWT de Supabase Auth y determinar la empresa a partir de una membresía autorizada.
- No se debe confiar en un `id_empresa` enviado por el cliente como prueba de autorización.
- La clave `service_role`, si se utiliza para tareas que lo requieran, debe permanecer exclusivamente en el backend y no exponerse a Angular.

**Motivo:** un filtro olvidado o la manipulación del identificador de empresa no deben permitir acceder a datos de otra empresa.

Estas reglas son decisiones de arquitectura. Todavía deben implementarse y probarse el contexto JWT, los privilegios y las políticas definitivas.

### 3.4 No modificar permisos ni políticas hasta cerrar el diseño

**Decisión:** no conceder todavía privilegios de tablas o secuencias, modificar las políticas existentes ni habilitar RLS en `rol` únicamente para corregir los resultados de la auditoría.

**Motivo:** los permisos deben derivarse de las operaciones reales de cada componente y del modelo de conexión local/remoto. Las concesiones parciales podrían dar una falsa sensación de seguridad.

Los cambios deberán implementarse mediante migraciones revisables de Alembic.

### 3.5 Validar RLS con usuarios y empresas diferentes

**Decisión:** antes de considerar lista la seguridad multiempresa, ejecutar pruebas de integración con al menos dos usuarios y dos empresas.

Las pruebas deben verificar que:

- Un usuario activo solo pueda acceder a los datos de su empresa.
- Una membresía inactiva no autorice operaciones.
- El dashboard financiero esté restringido al rol `Administrador`.
- No se puedan asociar ventas, detalles, gastos o movimientos a datos de otra empresa.
- Las lecturas y escrituras permitidas y denegadas se comporten como se espera.

La auditoría declarativa actual no equivale a estas pruebas de comportamiento.

## 4. Pendientes que no deben tratarse como decisiones aprobadas

1. **Tabla `rol`:** definir si debe habilitarse RLS y qué operaciones de lectura necesita la aplicación.
2. **Roles locales y remotos:** definir cómo reproducir de forma segura los roles y el contexto JWT en las pruebas locales, sin asumir que los roles de Supabase existen en la base local.
3. **Privilegios de aplicación:** preparar una matriz por tabla y operación (`SELECT`, `INSERT`, `UPDATE`, `DELETE`) y determinar los permisos mínimos necesarios sobre las secuencias.
4. **`FORCE ROW LEVEL SECURITY`:** evaluar sus efectos sobre los propietarios, las migraciones y las tareas administrativas. No se ha decidido habilitarlo.
5. **Funciones con `EXECUTE` para `PUBLIC`:** evaluar si conviene revocar el permiso general y concederlo explícitamente a roles concretos. No se ha aplicado ni aprobado aún esa modificación.
6. **Historial y borrados:** revisar las claves foráneas y las operaciones permitidas para evitar eliminar ventas completadas, facturas o movimientos de inventario accidentalmente.
7. **Stock:** definir la actualización transaccional de `producto.stock_actual`, la prevención de stock negativo bajo concurrencia y la reversión mediante movimientos trazables.
8. **Membresías concurrentes:** evaluar cómo evitar que una membresía se desactive concurrentemente con una operación que exige que permanezca activa.

## 5. Próximos pasos recomendados

1. Cerrar la matriz de permisos por tabla y operación, incluidos el dashboard y la configuración de la empresa.
2. Definir las pruebas de autenticación/JWT y el modelo de conexión del backend en local y en Supabase.
3. Preparar migraciones Alembic revisables para las correcciones aprobadas; no ejecutar DDL manual en producción.
4. Crear pruebas de integración RLS multiempresa con dos usuarios y dos empresas.
5. Revisar las reglas de stock, estados y retención histórica antes de habilitar las escrituras correspondientes.

## 6. Mantenimiento del documento

Los hallazgos describen el estado observado en la fecha de la auditoría; no son una garantía permanente. Después de cambiar políticas, privilegios, funciones o roles, actualizar este documento con la decisión, su motivo, la migración asociada y el resultado de las pruebas.


---

## 7. Respaldo, recuperación y continuidad operativa

**Fecha de validación: 26/11/2026**

### 7.1 Inventario de respaldos

| Archivo | Tamaño | SHA-256 |
|---|---:|---|
| `iondu_pre_migraciones_20261126_172942.dump` | 138.197 bytes | `DE7DCFEB5D63C7407BD164A7431C82928A5ADAB49C639A10530A8F7F8611045F` |
| `iondu_post_migraciones_20261126.dump` | 167.199 bytes | `6DC06D8A84185B58F60C4D830ACBD76E26D772CF58ABC1EEFD41B0C3D2B40130` |
| `iondu_roles_20261126.sql` | 1.572 bytes | `F8BC78A88D7B95ED87ABCC96CA622E1E17F7C0C0004FB43504510D4EFA90F985` |

Los respaldos PostgreSQL utilizan formato CUSTOM. El archivo de roles contiene definiciones globales sin contraseñas.

### 7.2 Versiones y punto de recuperación

- PostgreSQL y herramientas de respaldo: `17.11`.
- Versión Alembic posterior a migraciones: `fd09a182da8d`.
- Tamaño observado de la base: aproximadamente `9.606 kB`.
- El respaldo anterior a migraciones recuperó `c4e6a8b0d215`.

### 7.3 Pruebas de restauración

Ambos respaldos fueron inspeccionados con `pg_restore --list` y restaurados correctamente en bases aisladas, con código de salida 0.

La restauración posterior a migraciones coincidió con la base original en:

- 25 tablas públicas y 1 tabla `auth`.
- 23 tablas con RLS habilitado y forzado.
- 42 políticas RLS públicas.
- 129 restricciones y 74 índices.
- 4 funciones públicas.
- Privilegios efectivos de `iondu_app`, `iondu_auth`, `iondu_migrator` e `iondu_worker`.
- Versión Alembic `fd09a182da8d`.

Las pruebas no sobrescribieron la base operativa `iondu`. Las bases auxiliares de restauración se conservaron.

### 7.4 Procedimiento de recuperación

La restauración debe realizarse en una base nueva o expresamente designada. Nunca utilizar `iondu` como destino de pruebas destructivas.

1. Verificar la existencia, integridad y SHA-256 del respaldo.
2. En un clúster nuevo, revisar y recuperar los roles con un administrador. El archivo no contiene contraseñas:

```powershell
psql -U <ADMINISTRADOR> -d postgres -X -v ON_ERROR_STOP=1 -f backups/iondu_roles_20261126.sql
```

3. Crear una base independiente:

```powershell
createdb -U <ADMINISTRADOR> -T template0 -O iondu <BASE_NUEVA>
```

4. Restaurar el respaldo posterior a migraciones:

```powershell
pg_restore -U iondu -d <BASE_NUEVA> --single-transaction --exit-on-error backups/iondu_post_migraciones_20261126.dump
```

Para recuperar el estado anterior a las migraciones posteriores, utilizar `iondu_pre_migraciones_20261126_172942.dump` en el comando de restauración.

Los marcadores entre < > deben sustituirse por valores válidos. Estos comandos documentan el procedimiento; no deben ejecutarse sobre la base operativa.

5. Verificar tablas, restricciones, índices, funciones, triggers, políticas RLS, privilegios, versión Alembic y conectividad antes de habilitar la base recuperada.

### 7.5 Protección y mantenimiento

- Restringir el acceso a los archivos de respaldo.
- No publicar respaldos ni credenciales en repositorios.
- Restablecer las contraseñas por separado mediante configuración segura.
- No documentar valores de `.env` ni claves de almacenamiento.
- Mantener respaldos anteriores y posteriores a cambios importantes.
- Repetir una restauración de validación después de cambios importantes de esquema o privilegios.
- La restauración PostgreSQL no recupera automáticamente archivos externos ni credenciales.
- Toda recuperación real requiere identificar el punto de restauración y autorizar la intervención sobre la base de destino.
