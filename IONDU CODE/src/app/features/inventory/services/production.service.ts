import { Injectable, inject, signal } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { ProductionRun } from '../models/adjustment.model';
import { simulateRequest } from '../../../core/services/mock-http.util';
import { generateId } from '../../../core/utils/id.util';
import { RecipesService } from './recipes.service';
import { ProductsService } from './products.service';
import { AuditService } from '../../../core/services/audit.service';
import { AuthService } from '../../../core/services/auth.service';

export interface IngredientRequirement {
  productId: string;
  productName: string;
  unit: string;
  quantityNeeded: number;
  stockAvailable: number;
  stockAfter: number;
  sufficient: boolean;
}

@Injectable({ providedIn: 'root' })
export class ProductionService {
  private recipes = inject(RecipesService);
  private products = inject(ProductsService);
  private audit = inject(AuditService);
  private auth = inject(AuthService);

  #runs = signal<ProductionRun[]>([]);
  readonly runs = this.#runs.asReadonly();

  requirementsFor(recipeId: string, units: number): IngredientRequirement[] {
    const recipe = this.recipes.getRecipe(recipeId);
    if (!recipe) return [];
    const scale = units / recipe.yieldQuantity;

    return recipe.ingredients.map((ing) => {
      const product = this.products.getProduct(ing.productId);
      const quantityNeeded = Math.round(ing.quantity * scale * 1000) / 1000;
      const stockAvailable = product?.currentStock ?? 0;
      return {
        productId: ing.productId,
        productName: product?.name ?? 'Producto desconocido',
        unit: ing.unit,
        quantityNeeded,
        stockAvailable,
        stockAfter: Math.round((stockAvailable - quantityNeeded) * 1000) / 1000,
        sufficient: stockAvailable >= quantityNeeded,
      };
    });
  }

  estimatedCost(recipeId: string, units: number): number {
    const recipe = this.recipes.getRecipe(recipeId);
    if (!recipe) return 0;
    return Math.round(this.recipes.estimatedCost(recipe) * units * 100) / 100;
  }

  produce(recipeId: string, units: number): Observable<ProductionRun> {
    const recipe = this.recipes.getRecipe(recipeId);
    if (!recipe) return throwError(() => new Error('Receta no encontrada.'));

    const requirements = this.requirementsFor(recipeId, units);
    const shortage = requirements.find((r) => !r.sufficient);
    if (shortage) {
      return throwError(
        () => new Error(`Stock insuficiente de ${shortage.productName} para fabricar esta cantidad.`),
      );
    }

    const user = this.auth.currentUser();
    const userName = user?.fullName ?? 'Usuario';
    const product = this.products.getProduct(recipe.productId);
    const reference = `Fabricación de ${units} × ${recipe.name}`;

    requirements.forEach((req) => {
      this.products.applyStockChange({
        productId: req.productId,
        delta: -req.quantityNeeded,
        type: 'produccion_consumo',
        reference,
        createdBy: userName,
      });
    });

    this.products.applyStockChange({
      productId: recipe.productId,
      delta: units,
      type: 'produccion_ingreso',
      reference,
      createdBy: userName,
    });

    const run: ProductionRun = {
      id: generateId(),
      recipeId,
      productId: recipe.productId,
      productName: product?.name ?? recipe.name,
      unitsProduced: units,
      estimatedCost: this.estimatedCost(recipeId, units),
      date: new Date().toISOString(),
      producedBy: userName,
    };
    this.#runs.update((list) => [run, ...list]);

    this.audit.log({
      userId: user?.id ?? '',
      userName,
      module: 'inventario',
      action: 'Registró fabricación',
      description: `${userName} fabricó ${units} unidades de ${run.productName}.`,
    });

    return simulateRequest(run);
  }
}
