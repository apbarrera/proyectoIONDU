"""Carga datos demo en la base LOCAL de desarrollo para probar en Swagger y presentar.

Crea dos usuarios demo (Administrador y Operativo) en la empresa demo y le agrega
productos, clientes, proveedores, gastos, ventas de los últimos 30 días y movimientos
de inventario. Todo pasa por la API (mismas reglas que en producción); solo las fechas
de las ventas se mueven hacia atrás para que el historial se vea real.

Uso (con Docker encendido), desde backend/:
    $env:DATABASE_URL = "postgresql+psycopg://iondu:<clave>@127.0.0.1:15432/iondu"
    $env:APP_ENV = "development"
    .venv\\Scripts\\python.exe -m scripts.cargar_datos_demo

Si se define DEMO_PASSWORD (mínimo 10 caracteres), los dos usuarios demo pueden iniciar
sesión en el frontend con esa contraseña; si no, se les asigna después con
scripts/crear_usuario.py. En Swagger (/api/docs) también sirven los encabezados
X-Empresa-Id y X-Usuario-Id que imprime.
Solo funciona contra la base `iondu` de esta computadora y no se puede repetir: si la
empresa ya tiene productos, no hace nada.
"""

import os
import random
import sys
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select, text
from sqlalchemy.engine import make_url

ADMIN_DEMO = uuid.UUID("11111111-1111-1111-1111-111111111111")
OPERADOR_DEMO = uuid.UUID("22222222-2222-2222-2222-222222222222")
CORREO_ADMIN_DEMO = "admin@demo.iondu.ec"
CORREO_OPERADOR_DEMO = "operador@demo.iondu.ec"
RUC_EMPRESA = "1790016919001"
SERVIDORES_LOCALES = {"127.0.0.1", "localhost", "db"}
ZONA = ZoneInfo("America/Guayaquil")
# sku, nombre, categoría, precio, costo, código IVA, stock inicial, stock mínimo, extra
PRODUCTOS = (
    ("CAF-500", "Café en grano 500 g", "Cafés", 8.50, 5.00, "4", 150, 20, {}),
    ("CAF-250", "Café molido 250 g", "Cafés", 4.50, 2.60, "4", 200, 25, {}),
    ("PAN-CRO", "Croissant", "Panadería", 1.25, 0.45, "4", 400, 40, {}),
    ("PAN-YUC", "Pan de yuca (6 u.)", "Panadería", 2.00, 0.80, "0", 250, 30, {}),
    ("BEB-AGU", "Agua sin gas 500 ml", "Bebidas", 0.75, 0.30, "4", 14, 12, {}),
    (
        "INS-LEC",
        "Leche entera 1 L",
        "Insumos",
        0,
        1.10,
        "0",
        25,
        10,
        {"type": "insumo", "unit": "LITRO"},
    ),
    ("INS-AZU", "Azúcar 1 kg", "Insumos", 0, 1.10, "0", 4, 5, {"type": "insumo"}),
)


def _validar_destino() -> None:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        sys.exit("Define DATABASE_URL apuntando a la base local iondu.")
    destino = make_url(url)
    if destino.host not in SERVIDORES_LOCALES or destino.database != "iondu":
        sys.exit(f"Solo se cargan datos demo en la base local iondu, no en {destino.host}.")
    if os.environ.get("APP_ENV") != "development":
        sys.exit("Define APP_ENV=development: los datos demo son solo para desarrollo.")


def _sesion_admin():
    """Sesión con la credencial administrativa (MIGRATION_DATABASE_URL): crea la empresa y
    los usuarios demo y mueve fechas. Todo lo demás pasa por la API, como iondu_app."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from app.core.config import get_settings

    url = get_settings().migration_database_url or os.environ.get("DATABASE_URL", "")
    destino = make_url(url)
    if destino.host not in SERVIDORES_LOCALES or destino.database != "iondu":
        sys.exit("MIGRATION_DATABASE_URL debe apuntar a la base local iondu.")
    return Session(create_engine(destino))


def _preparar_usuarios(db) -> int:
    """Roles, empresa demo y los dos usuarios demo con su pertenencia."""
    from app.core import contrasenas
    from app.models import Empresa, Rol, Usuario, UsuarioEmpresa
    from app.models.rol import ADMINISTRADOR, OPERATIVO

    roles = {r.nombre: r.id_rol for r in db.scalars(select(Rol))}
    for nombre in (ADMINISTRADOR, OPERATIVO):
        if nombre not in roles:
            rol = Rol(nombre=nombre)
            db.add(rol)
            db.flush()
            roles[nombre] = rol.id_rol

    empresa = db.scalar(select(Empresa).where(Empresa.ruc == RUC_EMPRESA))
    if empresa is None:
        empresa = Empresa(
            razon_social="CAFETERÍA DEMO S.A.",
            nombre_comercial="Café Demo",
            ruc=RUC_EMPRESA,
            correo_electronico="demo@iondu.ec",
        )
        db.add(empresa)
        db.flush()

    clave_demo = os.environ.get("DEMO_PASSWORD")
    if clave_demo:
        try:
            contrasenas.validar_nueva(clave_demo)
        except ValueError as exc:
            sys.exit(f"DEMO_PASSWORD: {exc}")
    for usuario, correo, rol, nombre in (
        (ADMIN_DEMO, CORREO_ADMIN_DEMO, ADMINISTRADOR, "Admin Demo"),
        (OPERADOR_DEMO, CORREO_OPERADOR_DEMO, OPERATIVO, "Operador Demo"),
    ):
        cuenta = db.get(Usuario, usuario)
        if cuenta is None:
            cuenta = Usuario(id=usuario, email=correo, password_hash="!")
            db.add(cuenta)
        elif cuenta.email.endswith("@pendiente.invalid"):  # migrado desde auth.users
            cuenta.email = correo
        if clave_demo:
            cuenta.password_hash = contrasenas.hashear(clave_demo)
        db.flush()
        if db.get(UsuarioEmpresa, (usuario, empresa.id_empresa)) is None:
            db.add(
                UsuarioEmpresa(
                    id_usuario=usuario,
                    id_empresa=empresa.id_empresa,
                    id_rol=roles[rol],
                    nombre_visible=nombre,
                    estado="ACTIVO",
                )
            )
    db.commit()
    return empresa.id_empresa


def _ok(response, esperado: int = 201) -> dict:
    if response.status_code != esperado:
        sys.exit(f"Falló {response.request.method} {response.request.url}: {response.text}")
    return response.json()


def main() -> None:
    _validar_destino()
    from fastapi.testclient import TestClient

    from app.main import app
    from app.models import Producto

    with _sesion_admin() as db:
        id_empresa = _preparar_usuarios(db)
        if db.scalar(select(Producto.id_producto).where(Producto.id_empresa == id_empresa)):
            print("La empresa demo ya tiene productos: no se cargó nada.")
            _imprimir_ayuda(id_empresa)
            return

    admin = {"X-Empresa-Id": str(id_empresa), "X-Usuario-Id": str(ADMIN_DEMO)}
    operador = {"X-Empresa-Id": str(id_empresa), "X-Usuario-Id": str(OPERADOR_DEMO)}
    api = TestClient(app)

    def post(ruta, cuerpo, headers=admin, esperado=201):
        return _ok(api.post(f"/api{ruta}", json=cuerpo, headers=headers), esperado)

    _ok(
        api.put(
            "/api/company/billing-settings",
            json={
                "environment": "pruebas",
                "establishment": "001",
                "emissionPoint": "001",
                "requiredToKeepAccounts": False,
                "rimpe": True,
                "specialTaxpayer": None,
            },
            headers=admin,
        ),
        200,
    )

    # ---------- Productos ----------
    categorias = {
        nombre: post("/product-categories", {"name": nombre})["id"]
        for nombre in ("Cafés", "Panadería", "Bebidas", "Insumos")
    }
    productos = {}
    for sku, nombre, cat, precio, costo, iva, stock, minimo, extra in PRODUCTOS:
        productos[sku] = post(
            "/products",
            {
                "sku": sku,
                "name": nombre,
                "categoryId": categorias[cat],
                "salePrice": precio,
                "cost": costo,
                "vatPercentageCode": iva,
                "currentStock": stock,
                "minStock": minimo,
            }
            | extra,
        )["id"]

    # ---------- Clientes y proveedores ----------
    clientes = [
        post("/customers", c)["id"]
        for c in (
            {"identification": "1710000009", "name": "Juan Pérez", "email": "juan@example.com"},
            {"identification": "0912345675", "name": "María Cedeño", "phone": "0991234567"},
            {
                "identification": "1704567898001",
                "name": "Comercial Andrade",
                "email": "compras@andrade.ec",
            },
        )
    ]
    proveedores = {
        p["name"]: post("/suppliers", p)["id"]
        for p in (
            {"identification": "0109876540001", "name": "Lácteos Andinos", "phone": "072345678"},
            {
                "identification": "1807654320001",
                "name": "Tostadora del Valle",
                "email": "ventas@tostadora.ec",
            },
            {"identification": "1704567898", "name": "Carlos Rivera (arriendo)"},
        )
    }

    # ---------- Gastos de los últimos 30 días ----------
    gastos_cat = {
        c["name"]: c["id"] for c in _ok(api.get("/api/expense-categories", headers=admin), 200)
    }
    hoy = datetime.now(ZONA).replace(hour=10, minute=0, second=0, microsecond=0)
    for dias, cat, prov, total, desc, metodo in (
        (28, "Arriendo", "Carlos Rivera (arriendo)", 450, "Arriendo del local", "transferencia"),
        (25, "Materia prima", "Tostadora del Valle", 180, "Café en grano (30 kg)", "transferencia"),
        (21, "Servicios", None, 35, "Internet del local", "tarjeta_debito"),
        (18, "Materia prima", "Lácteos Andinos", 66, "Leche (60 L)", "efectivo"),
        (14, "Servicios", None, 48.20, "Energía eléctrica", "transferencia"),
        (10, "Empaque", None, 22.80, "Vasos y fundas", "efectivo"),
        (7, "Transporte", None, 15, "Envío de pedidos", "efectivo"),
        (4, "Mantenimiento", None, 60, "Mantenimiento de la cafetera", "tarjeta_credito"),
        (2, "Materia prima", "Lácteos Andinos", 33, "Leche (30 L)", "efectivo"),
    ):
        post(
            "/expenses",
            {
                "categoryId": gastos_cat[cat],
                "supplierId": proveedores.get(prov) if prov else None,
                "total": total,
                "description": desc,
                "paymentMethod": metodo,
                "date": (hoy - timedelta(days=dias)).isoformat(),
            },
            headers=operador if dias % 2 else admin,
        )

    # ---------- Ventas (se registran hoy y luego se mueven a su fecha) ----------
    # De 3 a 5 ventas por día durante 30 días. La semilla fija hace que siempre salgan
    # los mismos datos, y se lleva la cuenta del stock para no vender lo que no hay.
    azar = random.Random(2026)
    disponible = {sku: stock for sku, *_, stock, _, _ in PRODUCTOS}
    cantidades = {"CAF-500": (1, 2), "CAF-250": (1, 3), "PAN-CRO": (2, 6), "PAN-YUC": (1, 4)}
    metodos = ("efectivo", "efectivo", "tarjeta_debito", "tarjeta_credito", "transferencia")
    ventas = []
    ahora = datetime.now(ZONA)
    for dias in range(29, -1, -1):
        for _ in range(azar.randint(3, 5)):
            items = []
            for sku in azar.sample(sorted(cantidades), azar.randint(1, 3)):
                cantidad = azar.randint(*cantidades[sku])
                if disponible[sku] - cantidad >= 15:
                    disponible[sku] -= cantidad
                    items.append({"productId": productos[sku], "quantity": cantidad})
            if not items:
                continue
            cliente = azar.choice([None, None, *clientes])
            venta = post(
                "/sales",
                {"customerId": cliente, "paymentMethod": azar.choice(metodos), "items": items},
                headers=azar.choice((admin, operador)),
            )
            hora = timedelta(hours=azar.randint(-2, 9), minutes=azar.randint(0, 59))
            ventas.append((venta["id"], min(hoy - timedelta(days=dias) + hora, ahora)))

    with _sesion_admin() as db:
        for id_venta, fecha in ventas:
            db.execute(
                text("UPDATE venta SET fecha = :f WHERE id_venta = :v AND id_empresa = :e"),
                {"f": fecha, "v": id_venta, "e": id_empresa},
            )
            db.execute(
                text(
                    "UPDATE movimiento_inventario SET fecha = :f "
                    "WHERE motivo = :m AND id_empresa = :e"
                ),
                {"f": fecha, "m": f"Venta #{id_venta}", "e": id_empresa},
            )
        db.commit()

    # ---------- Inventario: entrada, salida y ajuste ----------
    post(
        "/inventory/movements",
        {
            "productId": productos["CAF-250"],
            "type": "entrada",
            "quantity": 20,
            "reason": "Llegó el pedido de la tostadora",
        },
        headers=operador,
    )
    post(
        "/inventory/movements",
        {
            "productId": productos["PAN-CRO"],
            "type": "salida",
            "quantity": 3,
            "reason": "Merma: se quemaron en el horno",
        },
        headers=operador,
    )
    post(
        "/inventory/adjustments",
        {"productId": productos["BEB-AGU"], "newStock": 6, "reason": "Conteo físico del viernes"},
    )

    print(
        "Datos demo cargados: 7 productos, 3 clientes, 3 proveedores, 9 gastos "
        f"y {len(ventas)} ventas."
    )
    _imprimir_ayuda(id_empresa)


def _imprimir_ayuda(id_empresa: int) -> None:
    if os.environ.get("DEMO_PASSWORD"):
        print("\nInicio de sesión (contraseña: la de DEMO_PASSWORD):")
        print(f"  {CORREO_ADMIN_DEMO}   (Administrador)")
        print(f"  {CORREO_OPERADOR_DEMO}   (Operativo)")
    print("\nEn Swagger (http://localhost:8080/api/docs) usa estos encabezados:")
    print(f"  X-Empresa-Id: {id_empresa}")
    print(f"  X-Usuario-Id: {ADMIN_DEMO}   (Admin Demo, Administrador)")
    print(f"  X-Usuario-Id: {OPERADOR_DEMO}   (Operador Demo, Operativo)")


if __name__ == "__main__":
    main()
