import { Injectable, computed, inject, signal } from '@angular/core';
import { Product } from '../models/product.model';
import { MovementType } from '../models/movement.model';
import { ProductsApiService } from './products-api.service';

/**
 * Productos de la empresa en memoria, cargados desde `/api/products`.
 *
 * Es la caché que comparten las pantallas de Inventario, Alertas y Ajustes; las altas y ediciones
 * de la pantalla de Productos pasan por `ProductsApiService`. Cada pantalla llama a `refresh()`
 * al abrirse.
 */
@Injectable({ providedIn: 'root' })
export class ProductsService {
  private readonly api = inject(ProductsApiService);

  #products = signal<Product[]>([]);
  readonly products = this.#products.asReadonly();

  #loading = signal(false);
  readonly loading = this.#loading.asReadonly();

  readonly lowStockProducts = computed(() =>
    this.#products().filter((p) => p.active && p.currentStock <= p.minStock),
  );

  /** Vuelve a pedir los productos al backend (stock incluido). */
  refresh(): void {
    this.#loading.set(true);
    this.api.getProducts().subscribe({
      next: (products) => {
        this.#products.set(products);
        this.#loading.set(false);
      },
      // El interceptor ya mostró el error.
      error: () => this.#loading.set(false),
    });
  }

  getProduct(id: string): Product | undefined {
    return this.#products().find((p) => p.id === id);
  }

  /**
   * Cambia el stock solo en memoria. Lo usa únicamente Producción, que todavía es simulada
   * (el backend no tiene recetas ni fabricación). `type`, `reference` y `createdBy` no se guardan.
   */
  applyStockChange(params: {
    productId: string;
    delta: number;
    type: MovementType;
    reference: string;
    createdBy: string;
  }): number {
    const product = this.getProduct(params.productId);
    if (!product) throw new Error('Producto no encontrado.');

    const resultingStock = Math.round((product.currentStock + params.delta) * 1000) / 1000;
    this.#products.update((list) =>
      list.map((p) => (p.id === params.productId ? { ...p, currentStock: resultingStock } : p)),
    );
    return resultingStock;
  }
}
