export type ProductType = 'venta' | 'insumo' | 'ambos';

export interface Product {
  id: string;
  sku: string;
  name: string;
  description?: string | null;
  category: string;
  categoryId?: number;
  type: ProductType;
  unit: string;
  salePrice: number | null;
  cost: number;
  currentStock: number;
  minStock: number;
  active: boolean;
}
