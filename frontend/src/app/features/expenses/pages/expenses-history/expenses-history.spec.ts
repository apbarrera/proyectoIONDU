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
      .flush({
        items: [expenseDto(2), expenseDto(1, 'anulado')],
        total: 2,
        page: 1,
        pageSize: 100,
      });
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

  it('edita un gasto enviando solo los campos que cambiaron', () => {
    const expense = component.expensesService.expenses()[0];
    component.open(expense);
    component.startEdit(expense);
    httpMock.expectOne('/api/expense-categories').flush([
      { id: 1, name: 'Servicios', description: null, predefined: true },
      { id: 2, name: 'Arriendo', description: null, predefined: true },
    ]);

    component.editForm.patchValue({ categoryId: 2, total: 12.5 });
    component.saveEdit(expense);

    const req = httpMock.expectOne('/api/expenses/2');
    expect(req.request.method).toBe('PATCH');
    expect(req.request.body).toEqual({ categoryId: 2, total: 12.5 });
    req.flush({ ...expenseDto(2), categoryId: 2, categoryName: 'Arriendo', total: 12.5 });

    expect(component.editing()).toBe(false);
    expect(component.selected()?.category).toBe('Arriendo');
  });

  it('al escribir un RUC nuevo busca o crea el proveedor antes de guardar', () => {
    const expense = component.expensesService.expenses()[0];
    component.startEdit(expense);
    httpMock.expectOne('/api/expense-categories').flush([]);

    component.editForm.patchValue({ providerRuc: '1790016919001', providerName: 'Favorita' });
    component.saveEdit(expense);

    httpMock
      .expectOne((r) => r.url === '/api/suppliers/lookup')
      .flush(null, { status: 404, statusText: 'Not Found' });
    const create = httpMock.expectOne((r) => r.url === '/api/suppliers' && r.method === 'POST');
    create.flush({
      id: 9,
      identification: '1790016919001',
      name: 'Favorita',
      phone: null,
      email: null,
      address: null,
      identificationWarning: null,
    });

    const req = httpMock.expectOne('/api/expenses/2');
    expect(req.request.body).toEqual({ supplierId: 9 });
    req.flush({
      ...expenseDto(2),
      supplierId: 9,
      supplierName: 'Favorita',
      supplierIdentification: '1790016919001',
    });
  });

  it('pide el nombre del proveedor si se escribe un RUC', () => {
    const expense = component.expensesService.expenses()[0];
    component.startEdit(expense);
    httpMock.expectOne('/api/expense-categories').flush([]);

    component.editForm.patchValue({ providerRuc: '1790016919001', providerName: ' ' });
    component.saveEdit(expense);

    httpMock.expectNone((r) => r.url.startsWith('/api/suppliers'));
    expect(component.editError('providerName')).toBe('Este campo es obligatorio.');
  });

  it('sin cambios no llama al backend', () => {
    const expense = component.expensesService.expenses()[0];
    component.startEdit(expense);
    httpMock.expectOne('/api/expense-categories').flush([]);

    component.saveEdit(expense);
    httpMock.expectNone('/api/expenses/2');
    expect(component.editing()).toBe(false);
  });
});
