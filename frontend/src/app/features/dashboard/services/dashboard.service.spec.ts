import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { DashboardService } from './dashboard.service';
import { buildRecommendations } from '../../recommendations/services/recommendations.service';
import { EMPTY_DASHBOARD_SUMMARY } from '../models/dashboard-summary.model';

describe('DashboardService', () => {
  let service: DashboardService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(DashboardService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('pide el período al backend y convierte los ids a texto', () => {
    let summary = EMPTY_DASHBOARD_SUMMARY;
    service.summary({ option: 'esteMes', from: '2026-11-01', to: '2026-11-20' }).subscribe((s) => (summary = s));

    const req = httpMock.expectOne((r) => r.url === '/api/dashboard');
    expect(req.request.params.get('from')).toBe('2026-11-01');
    expect(req.request.params.get('to')).toBe('2026-11-20');
    req.flush({
      from: '2026-11-01',
      to: '2026-11-20',
      income: 2240.8,
      expenses: 910,
      profit: 1330.8,
      salesCount: 125,
      expensesCount: 9,
      averageTicket: 17.93,
      topProducts: [{ productId: 1, name: 'Café', unitsSold: 98, revenue: 833 }],
      dailySeries: [{ date: '2026-11-01', income: 74.5, expenses: 0 }],
      expensesByCategory: [{ categoryId: 6, name: 'Arriendo', total: 450 }],
      inventory: {
        activeProducts: 7,
        lowStockCount: 1,
        inventoryValue: 691.5,
        lowStockProducts: [{ productId: 5, name: 'Agua', unit: 'UNIDAD', currentStock: 6, minStock: 12 }],
      },
    });

    expect(summary.profit).toBe(1330.8);
    expect(summary.topProducts[0].productId).toBe('1');
    expect(summary.inventory.lowStockProducts[0].productId).toBe('5');
  });

  it('las recomendaciones salen de los indicadores reales', () => {
    const thisMonth = {
      ...EMPTY_DASHBOARD_SUMMARY,
      income: 100,
      expenses: 150,
      profit: -50,
      inventory: {
        ...EMPTY_DASHBOARD_SUMMARY.inventory,
        lowStockProducts: [{ productId: '5', name: 'Agua', unit: 'UNIDAD', currentStock: 0, minStock: 12 }],
      },
    };
    const lastMonth = { ...EMPTY_DASHBOARD_SUMMARY, income: 500, expenses: 100 };

    const ids = buildRecommendations(thisMonth, lastMonth).map((r) => r.id);
    expect(ids).toEqual(['rec-sales-drop', 'rec-expenses-up', 'rec-negative-profit', 'rec-low-stock-5']);
  });
});
