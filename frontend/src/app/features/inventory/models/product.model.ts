export type ProductType = 'simple' | 'insumo';

export interface Product {
  id: string;
  sku: string;
  name: string;
  category: string;
  type: ProductType;
  unit: string;
  salePrice: number | null;
  cost: number;
  currentStock: number;
  minStock: number;
  active: boolean;
}
