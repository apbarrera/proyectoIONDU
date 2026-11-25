export type MovementType = 'entrada' | 'salida' | 'ajuste' | 'venta';

/** Tipos que el backend registra hoy (API.md, sección 12). Los de producción no existen en la base. */
export type BackendMovementType = 'entrada' | 'salida' | 'ajuste' | 'venta';

export interface InventoryMovement {
  id: string;
  productId: string;
  productName: string;
  unit?: string;
  type: MovementType;
  /** Con signo: positiva si entra al inventario, negativa si sale. */
  quantity: number;
  resultingStock: number;
  /** Motivo del movimiento (`reason` en el backend). */
  reference: string;
  date: string;
  createdBy: string;
}
