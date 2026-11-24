import { ComponentFixture, TestBed } from '@angular/core/testing';

import { KpiGrid } from './kpi-grid';
import { DashboardSummary, EMPTY_DASHBOARD_SUMMARY } from '../../models/dashboard-summary.model';

const MOCK_SUMMARY: DashboardSummary = {
  ...EMPTY_DASHBOARD_SUMMARY,
  income: 100,
  expenses: 40,
  profit: 60,
  salesCount: 2,
  averageTicket: 50,
};

describe('KpiGrid', () => {
  let component: KpiGrid;
  let fixture: ComponentFixture<KpiGrid>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [KpiGrid],
    }).compileComponents();

    fixture = TestBed.createComponent(KpiGrid);
    fixture.componentRef.setInput('summary', MOCK_SUMMARY);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
