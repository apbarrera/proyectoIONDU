export type MovementType =
  | 'entrada'
  | 'salida'
  | 'ajuste'
  | 'venta'
  | 'produccion_consumo'
  | 'produccion_ingreso';

export interface InventoryMovement {
  id: string;
  productId: string;
  productName: string;
  type: MovementType;
  quantity: number;
  resultingStock: number;
  reference: string;
  date: string;
  createdBy: string;
}
