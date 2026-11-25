export interface StockAdjustment {
  id: string;
  productId: string;
  productName: string;
  previousStock: number;
  newStock: number;
  quantityDelta: number;
  reason: string;
  date: string;
  createdBy: string;
}
