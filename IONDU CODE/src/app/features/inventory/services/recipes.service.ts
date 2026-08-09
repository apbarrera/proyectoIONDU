import { Injectable, inject, signal } from '@angular/core';
import { Observable } from 'rxjs';
import { Recipe } from '../models/recipe.model';
import { RECIPES_MOCK } from '../../../mocks/recipes.mock';
import { simulateRequest } from '../../../core/services/mock-http.util';
import { generateId } from '../../../core/utils/id.util';
import { ProductsService } from './products.service';

@Injectable({ providedIn: 'root' })
export class RecipesService {
  private products = inject(ProductsService);

  #recipes = signal<Recipe[]>(RECIPES_MOCK);
  readonly recipes = this.#recipes.asReadonly();

  getRecipes(): Observable<Recipe[]> {
    return simulateRequest(this.#recipes());
  }

  getRecipe(id: string): Recipe | undefined {
    return this.#recipes().find((r) => r.id === id);
  }

  estimatedCost(recipe: Recipe): number {
    const total = recipe.ingredients.reduce((sum, ing) => {
      const product = this.products.getProduct(ing.productId);
      return sum + (product?.cost ?? 0) * ing.quantity;
    }, 0);
    return Math.round((total / recipe.yieldQuantity) * 100) / 100;
  }

  createRecipe(input: Omit<Recipe, 'id'>): Observable<Recipe> {
    const recipe: Recipe = { ...input, id: generateId() };
    this.#recipes.update((list) => [recipe, ...list]);
    return simulateRequest(recipe);
  }

  updateRecipe(id: string, changes: Partial<Recipe>): Observable<Recipe> {
    this.#recipes.update((list) => list.map((r) => (r.id === id ? { ...r, ...changes } : r)));
    return simulateRequest(this.getRecipe(id)!);
  }

  deleteRecipe(id: string): Observable<void> {
    this.#recipes.update((list) => list.filter((r) => r.id !== id));
    return simulateRequest(undefined);
  }
}
