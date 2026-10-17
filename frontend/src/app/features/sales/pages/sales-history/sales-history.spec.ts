import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SalesHistory } from './sales-history';

describe('SalesHistory', () => {
  let component: SalesHistory;
  let fixture: ComponentFixture<SalesHistory>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SalesHistory],
    }).compileComponents();

    fixture = TestBed.createComponent(SalesHistory);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('une cada venta con su factura electrónica', () => {
    const withInvoice = component.rows().filter((row) => row.invoice);
    expect(withInvoice.length).toBeGreaterThan(0);
    expect(withInvoice.every((row) => row.invoice?.saleId === row.id)).toBe(true);
  });

  it('muestra primero las ventas más recientes', () => {
    const dates = component.rows().map((row) => row.date);
    expect(dates).toEqual([...dates].sort().reverse());
  });

  it('los filtros por estado reparten todas las ventas sin duplicar ni perder ninguna', () => {
    const counts = component.counts();
    expect(counts['authorized'] + counts['pending'] + counts['rejected'] + counts['none']).toBe(counts['all']);
  });

  it('el filtro "Sin factura" solo deja ventas sin factura', () => {
    component.filter.set('none');
    const rows = component.visibleRows();
    expect(rows.length).toBeGreaterThan(0);
    expect(rows.every((row) => !row.invoice)).toBe(true);
  });

  it('el filtro "Rechazadas" solo deja facturas rechazadas', () => {
    component.filter.set('rejected');
    expect(component.visibleRows().every((row) => row.invoice?.status === 'rechazada')).toBe(true);
  });

  it('valida la cédula o RUC antes de emitir o reintentar', () => {
    component.idDraft.set('123');
    expect(component.idError()).not.toBe('');
    component.idDraft.set('1790012345');
    expect(component.idError()).toBe('');
  });
});
