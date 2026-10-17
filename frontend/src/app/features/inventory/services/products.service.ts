import { Injectable, computed, inject, signal } from '@angular/core';
import { Observable } from 'rxjs';
import { Product } from '../models/product.model';
import { PRODUCTS_MOCK } from '../../../mocks/products.mock';
import { simulateRequest } from '../../../core/services/mock-http.util';
import { generateId } from '../../../core/utils/id.util';
import { MovementsService } from './movements.service';

@Injectable({ providedIn: 'root' })
export class ProductsService {
  private movements = inject(MovementsService);

  #products = signal<Product[]>(PRODUCTS_MOCK);
  readonly products = this.#products.asReadonly();

  readonly lowStockProducts = computed(() =>
    this.#products().filter((p) => p.active && p.currentStock <= p.minStock),
  );

  getProducts(): Observable<Product[]> {
    return simulateRequest(this.#products());
  }

  getProduct(id: string): Product | undefined {
    return this.#products().find((p) => p.id === id);
  }

  createProduct(input: Omit<Product, 'id'>): Observable<Product> {
    const product: Product = { ...input, id: generateId() };
    this.#products.update((list) => [product, ...list]);
    return simulateRequest(product);
  }

  updateProduct(id: string, changes: Partial<Product>): Observable<Product> {
    this.#products.update((list) => list.map((p) => (p.id === id ? { ...p, ...changes } : p)));
    return simulateRequest(this.getProduct(id)!);
  }

  /** Moves stock by a signed delta and writes the matching movement in one step. */
  applyStockChange(params: {
    productId: string;
    delta: number;
    type: Parameters<MovementsService['record']>[0]['type'];
    reference: string;
    createdBy: string;
  }): number {
    const product = this.getProduct(params.productId);
    if (!product) throw new Error('Producto no encontrado.');

    const resultingStock = Math.round((product.currentStock + params.delta) * 1000) / 1000;
    this.#products.update((list) =>
      list.map((p) => (p.id === params.productId ? { ...p, currentStock: resultingStock } : p)),
    );

    this.movements.record({
      productId: product.id,
      productName: product.name,
      type: params.type,
      quantity: params.delta,
      resultingStock,
      reference: params.reference,
      createdBy: params.createdBy,
    });

    return resultingStock;
  }
}
