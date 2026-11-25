import { Injectable, computed, inject, signal } from '@angular/core';
import { Observable } from 'rxjs';
import { Product, ProductType } from '../models/product.model';
import { PRODUCTS_MOCK } from '../../../mocks/products.mock';
import { simulateRequest } from '../../../core/services/mock-http.util';
import { generateId } from '../../../core/utils/id.util';
import { MovementsService } from './movements.service';

const SKU_PREFIX: Record<ProductType, string> = { simple: 'PS', insumo: 'IN' };

const SUGGESTED_CATEGORIES = ['Materia prima', 'Empaques', 'Bebidas', 'Insumos secos', 'Refrigerados', 'Otros'];

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

  /** Categorías ya usadas más unas sugeridas, sin repetir, para ofrecerlas al crear un producto. */
  readonly categories = computed(() => {
    const byKey = new Map<string, string>();
    for (const name of [...this.#products().map((p) => p.category), ...SUGGESTED_CATEGORIES]) {
      const key = name.trim().toLowerCase();
      if (key && !byKey.has(key)) byKey.set(key, name.trim());
    }
    return [...byKey.values()].sort((a, b) => a.localeCompare(b, 'es'));
  });

  /** Código que se asignará al próximo producto del tipo dado (PS-001 para productos, IN-001 para insumos). */
  nextSku(type: ProductType, taken: Iterable<string> = this.#products().map((p) => p.sku)): string {
    const prefix = SKU_PREFIX[type];
    const pattern = new RegExp(`^${prefix}-(\\d+)$`, 'i');
    let max = 0;
    for (const sku of taken) {
      const match = pattern.exec(sku);
      if (match) max = Math.max(max, Number(match[1]));
    }
    return `${prefix}-${String(max + 1).padStart(3, '0')}`;
  }

  /** Crea el producto; si no trae código, se genera uno automáticamente. */
  createProduct(input: Omit<Product, 'id'>): Observable<Product> {
    const [product] = this.#insert([input]);
    return simulateRequest(product);
  }

  /** Crea varios productos de una vez, generando el código de los que no lo traen. */
  createMany(inputs: Omit<Product, 'id'>[]): Observable<Product[]> {
    return simulateRequest(this.#insert(inputs));
  }

  #insert(inputs: Omit<Product, 'id'>[]): Product[] {
    const taken = new Set(this.#products().map((p) => p.sku));
    const created = inputs.map((input) => {
      const sku = input.sku.trim() || this.nextSku(input.type, taken);
      taken.add(sku);
      return { ...input, sku, id: generateId() } satisfies Product;
    });
    this.#products.update((list) => [...created, ...list]);
    return created;
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
