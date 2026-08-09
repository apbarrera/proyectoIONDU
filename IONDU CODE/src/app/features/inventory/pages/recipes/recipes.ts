import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RecipesService } from '../../services/recipes.service';
import { ProductsService } from '../../services/products.service';
import { Recipe } from '../../models/recipe.model';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { Button } from '../../../../shared/components/button/button';
import { Card } from '../../../../shared/components/card/card';
import { Modal } from '../../../../shared/components/modal/modal';
import { FormField } from '../../../../shared/components/form-field/form-field';
import { EmptyState } from '../../../../shared/components/empty-state/empty-state';
import { ConfirmDialogService } from '../../../../core/services/confirm-dialog.service';
import { ToastService } from '../../../../core/services/toast.service';

@Component({
  selector: 'app-recipes',
  imports: [ReactiveFormsModule, PageHeader, Button, Card, Modal, FormField, EmptyState],
  templateUrl: './recipes.html',
  styleUrl: './recipes.scss',
})
export class Recipes {
  recipesService = inject(RecipesService);
  productsService = inject(ProductsService);
  private confirmDialog = inject(ConfirmDialogService);
  private toast = inject(ToastService);
  private fb = inject(FormBuilder);

  formOpen = signal(false);
  editingId = signal<string | null>(null);

  form = this.fb.nonNullable.group({
    name: ['', Validators.required],
    productId: ['', Validators.required],
    description: [''],
    yieldQuantity: [1, [Validators.required, Validators.min(1)]],
    notes: [''],
    ingredients: this.fb.array<ReturnType<typeof this.newIngredientGroup>>([]),
  });

  get ingredients() {
    return this.form.controls.ingredients;
  }

  newIngredientGroup(productId = '', quantity = 0, unit = 'kg') {
    return this.fb.nonNullable.group({
      productId: [productId, Validators.required],
      quantity: [quantity, [Validators.required, Validators.min(0.01)]],
      unit: [unit, Validators.required],
    });
  }

  addIngredient(): void {
    this.ingredients.push(this.newIngredientGroup());
  }

  removeIngredient(index: number): void {
    this.ingredients.removeAt(index);
  }

  productName(id: string): string {
    return this.productsService.getProduct(id)?.name ?? 'Producto desconocido';
  }

  estimatedCost(recipe: Recipe): number {
    return this.recipesService.estimatedCost(recipe);
  }

  openCreate(): void {
    this.editingId.set(null);
    this.ingredients.clear();
    this.form.reset({ name: '', productId: '', description: '', yieldQuantity: 1, notes: '' });
    this.addIngredient();
    this.formOpen.set(true);
  }

  openEdit(recipe: Recipe): void {
    this.editingId.set(recipe.id);
    this.ingredients.clear();
    recipe.ingredients.forEach((ing) =>
      this.ingredients.push(this.newIngredientGroup(ing.productId, ing.quantity, ing.unit)),
    );
    this.form.reset({
      name: recipe.name,
      productId: recipe.productId,
      description: recipe.description,
      yieldQuantity: recipe.yieldQuantity,
      notes: recipe.notes ?? '',
    });
    this.formOpen.set(true);
  }

  save(): void {
    if (this.form.invalid || this.ingredients.length === 0) {
      this.form.markAllAsTouched();
      return;
    }
    const raw = this.form.getRawValue();
    const payload = {
      name: raw.name,
      productId: raw.productId,
      description: raw.description,
      yieldQuantity: raw.yieldQuantity,
      notes: raw.notes,
      ingredients: raw.ingredients,
    };

    const id = this.editingId();
    const request = id ? this.recipesService.updateRecipe(id, payload) : this.recipesService.createRecipe(payload);

    request.subscribe(() => {
      this.toast.success(id ? 'Receta actualizada.' : 'Receta creada.');
      this.formOpen.set(false);
    });
  }

  close(): void {
    this.formOpen.set(false);
  }

  deleteRecipe(recipe: Recipe): void {
    this.confirmDialog
      .confirm({
        title: 'Eliminar receta',
        message: `¿Eliminar la receta "${recipe.name}"? Esta acción no se puede deshacer.`,
        danger: true,
      })
      .subscribe((confirmed) => {
        if (!confirmed) return;
        this.recipesService.deleteRecipe(recipe.id).subscribe(() => this.toast.success('Receta eliminada.'));
      });
  }
}
