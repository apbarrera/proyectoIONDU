import { Injectable, computed, inject } from '@angular/core';
import { DashboardService } from '../../dashboard/services/dashboard.service';
import { ProductsService } from '../../inventory/services/products.service';
import { resolveDateRange } from '../../../shared/utils/date-range.util';
import { Recommendation } from '../models/recommendation.model';

/** Pure read-only aggregator — recommendations are informative only, never auto-applied. */
@Injectable({ providedIn: 'root' })
export class RecommendationsService {
  private dashboard = inject(DashboardService);
  private products = inject(ProductsService);

  readonly recommendations = computed<Recommendation[]>(() => {
    const list: Recommendation[] = [];

    const thisMonth = this.dashboard.summary(resolveDateRange('esteMes'));
    const lastMonth = this.dashboard.summary(resolveDateRange('mesAnterior'));

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

    this.products.lowStockProducts().forEach((product) => {
      list.push({
        id: `rec-low-stock-${product.id}`,
        title: `Stock bajo: ${product.name}`,
        description: `El producto "${product.name}" tiene ${product.currentStock} ${product.unit} en stock, por debajo del mínimo de ${product.minStock} ${product.unit}. Considera reabastecerlo pronto para evitar quiebres de stock.`,
        category: 'Inventario',
        relatedModule: 'Inventario',
        dataUsed: [`Stock actual de ${product.name}`, `Stock mínimo configurado`],
        priority: product.currentStock <= 0 ? 'alta' : 'media',
      });
    });

    if (thisMonth.topProducts.length > 0) {
      const top = thisMonth.topProducts[0];
      list.push({
        id: 'rec-top-product',
        title: `${top.name} es tu producto de mayor rotación`,
        description: `Este mes vendiste ${top.unitsSold} unidades de ${top.name}, generando $${top.revenue.toFixed(2)}. Asegúrate de mantener suficiente stock e ingredientes disponibles.`,
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
  });
}
