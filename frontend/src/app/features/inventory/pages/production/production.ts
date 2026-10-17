import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ProductionService } from '../../services/production.service';
import { RecipesService } from '../../services/recipes.service';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { Button } from '../../../../shared/components/button/button';
import { Card } from '../../../../shared/components/card/card';
import { ToastService } from '../../../../core/services/toast.service';
import { Icon } from '../../../../shared/components/icon/icon';

@Component({
  selector: 'app-production',
  imports: [FormsModule, PageHeader, Button, Card, Icon],
  templateUrl: './production.html',
  styleUrl: './production.scss',
})
export class Production {
  recipesService = inject(RecipesService);
  productionService = inject(ProductionService);
  private toast = inject(ToastService);

  selectedRecipeId = signal('');
  units = signal(1);
  submitting = signal(false);

  requirements = computed(() => {
    if (!this.selectedRecipeId()) return [];
    return this.productionService.requirementsFor(this.selectedRecipeId(), this.units());
  });

  estimatedCost = computed(() => {
    if (!this.selectedRecipeId()) return 0;
    return this.productionService.estimatedCost(this.selectedRecipeId(), this.units());
  });

  canProduce = computed(() => this.requirements().length > 0 && this.requirements().every((r) => r.sufficient));

  confirmProduction(): void {
    if (!this.canProduce() || this.submitting()) return;
    this.submitting.set(true);

    this.productionService.produce(this.selectedRecipeId(), this.units()).subscribe({
      next: (run) => {
        this.toast.success(`Fabricación completada: ${run.unitsProduced} × ${run.productName}.`);
        this.units.set(1);
        this.submitting.set(false);
      },
      error: (err: Error) => {
        this.toast.error(err.message);
        this.submitting.set(false);
      },
    });
  }
}
