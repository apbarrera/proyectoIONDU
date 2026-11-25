import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { ExpensesHistory } from './expenses-history';

const expenseDto = (id: number, status = 'confirmado') => ({
  id,
  date: '2026-11-20T10:30:00-05:00',
  categoryId: 1,
  categoryName: 'Servicios',
  supplierId: null,
  supplierName: null,
  supplierIdentification: null,
  total: 10,
  description: 'Pago de internet',
  paymentMethod: 'transferencia',
  receiptNumber: null,
  status,
  source: 'manual',
});

describe('ExpensesHistory', () => {
  let component: ExpensesHistory;
  let fixture: ComponentFixture<ExpensesHistory>;
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ExpensesHistory],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();

    httpMock = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(ExpensesHistory);
    component = fixture.componentInstance;
    await fixture.whenStable();

    httpMock
      .expectOne((r) => r.url === '/api/expenses')
      .flush({ items: [expenseDto(2), expenseDto(1, 'anulado')], total: 2, page: 1, pageSize: 100 });
  });

  afterEach(() => httpMock.verify());

  it('los gastos anulados no cuentan en el total', () => {
    expect(component.expensesService.expenses().length).toBe(2);
    expect(component.expensesService.totalExpenses()).toBe(10);
  });

  it('anula un gasto con el motivo escrito', () => {
    component.open(component.expensesService.expenses()[0]);
    component.voidReason.set('Registrado dos veces');
    component.confirmVoid(component.selected()!);

    const req = httpMock.expectOne('/api/expenses/2/void');
    expect(req.request.body).toEqual({ reason: 'Registrado dos veces' });
    req.flush(expenseDto(2, 'anulado'));

    expect(component.selected()?.status).toBe('anulado');
    expect(component.expensesService.totalExpenses()).toBe(0);
  });

  it('no envía la anulación sin un motivo', () => {
    component.voidReason.set('');
    component.confirmVoid(component.expensesService.expenses()[0]);
    httpMock.expectNone('/api/expenses/2/void');
  });
});
