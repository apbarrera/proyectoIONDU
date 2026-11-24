import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { ExpensesService } from './expenses.service';

describe('ExpensesService', () => {
  let service: ExpensesService;
  let httpMock: HttpTestingController;

  const categories = [
    { id: 1, name: 'Servicios', description: null, predefined: true },
    { id: 7, name: 'Otros gastos operativos', description: null, predefined: true },
  ];

  const expenseDto = (id: number) => ({
    id,
    date: '2026-11-20T10:30:00-05:00',
    categoryId: 1,
    categoryName: 'Servicios',
    supplierId: 4,
    supplierName: 'Corporación Favorita',
    supplierIdentification: '1790016919001',
    total: 25.5,
    description: 'Pago de internet',
    paymentMethod: 'transferencia',
    receiptNumber: null,
    status: 'confirmado',
    source: 'manual',
  });

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(ExpensesService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('descarga los gastos y los convierte al modelo del frontend', () => {
    service.getExpenses().subscribe();
    httpMock
      .expectOne((r) => r.url === '/api/expenses')
      .flush({ items: [expenseDto(12)], total: 1, page: 1, pageSize: 100 });

    const expense = service.expenses()[0];
    expect(expense.id).toBe('12');
    expect(expense.category).toBe('Servicios');
    expect(expense.providerRuc).toBe('1790016919001');
    expect(expense.sourceType).toBe('manual');
    expect(service.totalExpenses()).toBe(25.5);
  });

  it('registra un gasto sin proveedor: resuelve la categoría por nombre y no crea proveedor', () => {
    service
      .createExpense({
        date: '2026-11-20T12:00:00',
        category: 'servicios',
        providerName: '',
        providerRuc: '',
        total: 25.5,
        paymentMethod: 'efectivo',
        description: ' Pago de internet ',
      })
      .subscribe();

    httpMock.expectOne('/api/expense-categories').flush(categories);
    const req = httpMock.expectOne((r) => r.url === '/api/expenses' && r.method === 'POST');
    expect(req.request.body).toEqual({
      categoryId: 1,
      supplierId: null,
      total: 25.5,
      description: 'Pago de internet',
      paymentMethod: 'efectivo',
      date: '2026-11-20T12:00:00',
      receiptNumber: null,
    });
    req.flush(expenseDto(13));

    expect(service.expenses()[0].id).toBe('13');
  });

  it('una categoría desconocida va a "Otros gastos operativos"', () => {
    service
      .createExpense({
        date: '2026-11-20T12:00:00',
        category: 'Insumos',
        providerName: '',
        providerRuc: '',
        total: 10,
        paymentMethod: 'efectivo',
        description: 'Compra',
      })
      .subscribe();

    httpMock.expectOne('/api/expense-categories').flush(categories);
    const req = httpMock.expectOne((r) => r.url === '/api/expenses' && r.method === 'POST');
    expect(req.request.body.categoryId).toBe(7);
    req.flush(expenseDto(14));
  });

  it('con RUC del proveedor lo busca o lo crea antes de guardar el gasto', () => {
    service
      .createExpense({
        date: '2026-11-20T12:00:00',
        category: 'Servicios',
        providerName: 'Corporación Favorita',
        providerRuc: '1790016919001',
        total: 25.5,
        paymentMethod: 'transferencia',
        description: 'Pago',
      })
      .subscribe();

    httpMock.expectOne('/api/expense-categories').flush(categories);
    httpMock
      .expectOne((r) => r.url === '/api/suppliers/lookup')
      .flush(null, { status: 404, statusText: 'Not Found' });
    httpMock
      .expectOne((r) => r.url === '/api/suppliers' && r.method === 'POST')
      .flush({
        id: 4,
        identification: '1790016919001',
        name: 'Corporación Favorita',
        phone: null,
        email: null,
        address: null,
        identificationWarning: null,
      });
    const req = httpMock.expectOne((r) => r.url === '/api/expenses' && r.method === 'POST');
    expect(req.request.body.supplierId).toBe(4);
    req.flush(expenseDto(15));
  });
});
