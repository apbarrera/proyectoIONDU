"""Modelos (tablas) de SQLAlchemy.

Importar aquí cada modelo nuevo, por ejemplo:
    from app.models.producto import Producto  # noqa: F401
Alembic hace `import app.models` y solo ve las tablas importadas en este archivo.
"""

from app.models.accion_ia import AccionIA  # noqa: F401
from app.models.categoria_gasto import CategoriaGasto  # noqa: F401
from app.models.categoria_producto import CategoriaProducto  # noqa: F401
from app.models.cliente import Cliente  # noqa: F401
from app.models.consumo_tokens import ConsumoTokens  # noqa: F401
from app.models.dashboard_financiero import DashboardFinanciero  # noqa: F401
from app.models.detalle_venta import DetalleVenta  # noqa: F401
from app.models.empresa import Empresa  # noqa: F401
from app.models.factura import Factura  # noqa: F401
from app.models.gasto import Gasto  # noqa: F401
from app.models.movimiento_inventario import MovimientoInventario  # noqa: F401
from app.models.producto import Producto  # noqa: F401
from app.models.proveedor import Proveedor  # noqa: F401
from app.models.recomendacion import Recomendacion  # noqa: F401
from app.models.rol import Rol  # noqa: F401
from app.models.usuario_empresa import UsuarioEmpresa  # noqa: F401
from app.models.venta import Venta  # noqa: F401
