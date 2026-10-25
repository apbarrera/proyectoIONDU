"""Modelos (tablas) de SQLAlchemy.

Importar aquí cada modelo nuevo, por ejemplo:
    from app.models.producto import Producto  # noqa: F401
Alembic hace `import app.models` y solo ve las tablas importadas en este archivo.
"""

from app.models.categoria_producto import CategoriaProducto  # noqa: F401
from app.models.empresa import Empresa  # noqa: F401
from app.models.producto import Producto  # noqa: F401
