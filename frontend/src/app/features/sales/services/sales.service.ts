import { Injectable, computed, inject, signal } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { EMPTY, Observable, expand, map, reduce, tap } from 'rxjs';

import { environment } from '../../../../environments/environment';
import { PaymentMethod, Sale, SaleLineItem, SaleStatus } from '../models/sale.model';
import { InvoiceDto, invoiceFromDto } from '../../billing/models/invoice.mapper';

interface SaleItemDto {
  productId: number | null;
  productName: string;
  quantity: number;
  unitPrice: number;
  subtotal: number;
}

interface SaleDto {
  id: number;
  date: string;
  customerId: number | null;
  customerName: string;
  customerIdentification: string | null;
  items: SaleItemDto[];
  subtotal: number;
  ivaAmount: number;
  total: number;
  paymentMethod: PaymentMethod;
  status: SaleStatus;
  observation: string | null;
  createdBy: string | null;
  invoice: InvoiceDto | null;
}

interface SalePageDto {
  items: SaleDto[];
  total: number;
  page: number;
  pageSize: number;
}

/** Línea de producto: el precio y el IVA los pone el backend a partir del producto. */
export interface NewSaleInput {
  /** `null` = consumidor final. */
  customerId: number | null;
  items: { productId: number; quantity: number }[];
  paymentMethod: PaymentMethod;
  observation?: string;
}

@Injectable({ providedIn: 'root' })
export class SalesService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/sales`;

  #sales = signal<Sale[]>([]);
  readonly sales = this.#sales.asReadonly();

  readonly totalRevenue = computed(() =>
    this.#sales()
      .filter((s) => s.status === 'completada')
      .reduce((sum, s) => sum + s.total, 0),
  );

  /** Descarga todo el historial (de 100 en 100) y actualiza `sales`. */
  getSales(): Observable<Sale[]> {
    const getPage = (page: number) =>
      this.http.get<SalePageDto>(this.baseUrl, {
        params: new HttpParams().set('page', page).set('pageSize', 100),
      });

    return getPage(1).pipe(
      expand((result) =>
        result.page * result.pageSize < result.total ? getPage(result.page + 1) : EMPTY,
      ),
      reduce((all, result) => [...all, ...result.items], [] as SaleDto[]),
      map((items) => items.map((item) => this.toSale(item))),
      tap((sales) => this.#sales.set(sales)),
    );
  }

  /** Registra la venta: el backend descuenta el stock y guarda el movimiento en una sola transacción. */
  createSale(input: NewSaleInput): Observable<Sale> {
    const body = {
      customerId: input.customerId,
      items: input.items.map((item) => ({
        productId: item.productId,
        quantity: item.quantity,
        discount: 0,
      })),
      paymentMethod: input.paymentMethod,
      observation: input.observation?.trim() || null,
    };

    return this.http.post<SaleDto>(this.baseUrl, body).pipe(
      map((dto) => this.toSale(dto)),
      tap((sale) => this.#sales.update((list) => [sale, ...list])),
    );
  }

  /**
   * Anula la venta (solo Administrador): el backend devuelve el stock y la deja como `anulada`.
   * Una venta con factura autorizada o en proceso no se anula aquí (requiere nota de crédito).
   */
  voidSale(id: string, reason: string): Observable<Sale> {
    return this.http
      .post<SaleDto>(`${this.baseUrl}/${encodeURIComponent(id)}/void`, { reason: reason.trim() })
      .pipe(
        map((dto) => this.toSale(dto)),
        tap((sale) => this.#sales.update((list) => list.map((s) => (s.id === sale.id ? sale : s)))),
      );
  }

  private toSale(dto: SaleDto): Sale {
    const items: SaleLineItem[] = dto.items.map((item) => ({
      productId: item.productId === null ? '' : String(item.productId),
      productName: item.productName,
      quantity: item.quantity,
      unitPrice: item.unitPrice,
      subtotal: item.subtotal,
    }));

    const sale: Sale = {
      id: String(dto.id),
      folio: String(dto.id).padStart(6, '0'),
      date: dto.date,
      customerId: dto.customerId,
      customerName: dto.customerName,
      customerIdentification: dto.customerIdentification,
      items,
      subtotal: dto.subtotal,
      ivaAmount: dto.ivaAmount,
      total: dto.total,
      paymentMethod: dto.paymentMethod,
      status: dto.status,
      observation: dto.observation ?? undefined,
      createdBy: dto.createdBy ?? undefined,
    };
    if (dto.invoice) sale.invoice = invoiceFromDto(dto.invoice, sale);
    return sale;
  }
}
