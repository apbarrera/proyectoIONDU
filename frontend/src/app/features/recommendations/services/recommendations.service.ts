import { HttpClient } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { forkJoin } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { DashboardService } from '../../dashboard/services/dashboard.service';
import { DashboardSummary } from '../../dashboard/models/dashboard-summary.model';
import { resolveDateRange } from '../../../shared/utils/date-range.util';
import { AiAnalysis, Recommendation } from '../models/recommendation.model';

/**
 * Recomendaciones basadas en reglas sobre los indicadores reales del dashboard (este mes contra el
 * mes anterior y el estado del inventario). Son solo informativas: nunca se aplican solas.
 * Como el dashboard es exclusivo del Administrador, para otros roles el backend responde 403.
 */
@Injectable({ providedIn: 'root' })
export class RecommendationsService {
  private dashboard = inject(DashboardService);

  #recommendations = signal<Recommendation[]>([]);
  readonly recommendations = this.#recommendations.asReadonly();

  #loading = signal(false);
  readonly loading = this.#loading.asReadonly();

  private http = inject(HttpClient);

  /** Último análisis con IA de esta sesión (se pide a demanda: gasta tokens). */
  #aiAnalysis = signal<AiAnalysis | null>(null);
  readonly aiAnalysis = this.#aiAnalysis.asReadonly();

  #aiLoading = signal(false);
  readonly aiLoading = this.#aiLoading.asReadonly();

  generateWithAi(): void {
    if (this.#aiLoading()) return;
    this.#aiLoading.set(true);
    this.http.post<AiAnalysis>(`${environment.apiUrl}/recommendations/ai`, null).subscribe({
      next: (analysis) => {
        this.#aiAnalysis.set(analysis);
        this.#aiLoading.set(false);
      },
      // El interceptor ya mostró el motivo (p. ej., límite de tokens alcanzado).
      error: () => this.#aiLoading.set(false),
    });
  }

  refresh(): void {
    this.#loading.set(true);
    forkJoin([
      this.dashboard.summary(resolveDateRange('esteMes')),
      this.dashboard.summary(resolveDateRange('mesAnterior')),
    ]).subscribe({
      next: ([thisMonth, lastMonth]) => {
        this.#recommendations.set(buildRecommendations(thisMonth, lastMonth));
        this.#loading.set(false);
      },
      // El interceptor ya mostró el error.
      error: () => this.#loading.set(false),
    });
  }
}

export function buildRecommendations(thisMonth: DashboardSummary, lastMonth: DashboardSummary): Recommendation[] {
  const list: Recommendation[] = [];

  if (lastMonth.income > 0 && thisMonth.income < lastMonth.income * 0.85) {
    const dropPct = Math.round((1 - thisMonth.income / lastMonth.income) * 100);
    list.push({
      id: 'rec-sales-drop',
      title: 'Tus ventas bajaron respecto al mes anterior',
      description: `Detectamos una caída del ${dropPct}% en ingresos este mes ($${thisMonth.income.toFixed(2)}) comparado con el mes anterior ($${lastMonth.income.toFixed(2)}). Considera revisar tus canales de venta o lanzar una promoción.`,
      category: 'Ventas',
      relatedModule: 'Dashboard',
      dataUsed: ['Ventas de este mes', 'Ventas del mes anterior'],
      priority: 'alta',
    });
  }

  if (lastMonth.expenses > 0 && thisMonth.expenses > lastMonth.expenses * 1.2) {
    const increasePct = Math.round((thisMonth.expenses / lastMonth.expenses - 1) * 100);
    list.push({
      id: 'rec-expenses-up',
      title: 'Tus gastos aumentaron significativamente',
      description: `Los gastos de este mes ($${thisMonth.expenses.toFixed(2)}) son un ${increasePct}% más altos que el mes anterior ($${lastMonth.expenses.toFixed(2)}). Revisa el historial de gastos para identificar la causa.`,
      category: 'Gastos',
      relatedModule: 'Gastos',
      dataUsed: ['Gastos de este mes', 'Gastos del mes anterior'],
      priority: 'media',
    });
  }

  if (thisMonth.profit < 0) {
    list.push({
      id: 'rec-negative-profit',
      title: 'Tu utilidad de este mes es negativa',
      description: `Con ingresos de $${thisMonth.income.toFixed(2)} y gastos de $${thisMonth.expenses.toFixed(2)}, tu utilidad actual es de $${thisMonth.profit.toFixed(2)}. Evalúa reducir gastos variables o ajustar precios.`,
      category: 'Finanzas',
      relatedModule: 'Dashboard',
      dataUsed: ['Ingresos de este mes', 'Gastos de este mes'],
      priority: 'alta',
    });
  }

  thisMonth.inventory.lowStockProducts.forEach((product) => {
    list.push({
      id: `rec-low-stock-${product.productId}`,
      title: `Stock bajo: ${product.name}`,
      description: `El producto "${product.name}" tiene ${product.currentStock} ${product.unit} en stock, por debajo del mínimo de ${product.minStock} ${product.unit}. Considera reabastecerlo pronto para evitar quiebres de stock.`,
      category: 'Inventario',
      relatedModule: 'Inventario',
      dataUsed: [`Stock actual de ${product.name}`, 'Stock mínimo configurado'],
      priority: product.currentStock <= 0 ? 'alta' : 'media',
    });
  });

  if (thisMonth.topProducts.length > 0) {
    const top = thisMonth.topProducts[0];
    list.push({
      id: 'rec-top-product',
      title: `${top.name} es tu producto de mayor rotación`,
      description: `Este mes vendiste ${top.unitsSold} unidades de ${top.name}, generando $${top.revenue.toFixed(2)}. Asegúrate de mantener suficiente stock disponible.`,
      category: 'Ventas',
      relatedModule: 'Inventario',
      dataUsed: ['Ventas de este mes por producto'],
      priority: 'baja',
    });

    const low = thisMonth.topProducts[thisMonth.topProducts.length - 1];
    if (thisMonth.topProducts.length > 1 && low.unitsSold < top.unitsSold * 0.2) {
      list.push({
        id: 'rec-low-rotation',
        title: `${low.name} tiene baja rotación`,
        description: `Solo se vendieron ${low.unitsSold} unidades de ${low.name} este mes. Evalúa una promoción o revisar su precio.`,
        category: 'Ventas',
        relatedModule: 'Inventario',
        dataUsed: ['Ventas de este mes por producto'],
        priority: 'baja',
      });
    }
  }

  return list;
}
