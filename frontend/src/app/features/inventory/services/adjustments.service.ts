import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, map, tap } from 'rxjs';

import { environment } from '../../../../environments/environment';
import { StockAdjustment } from '../models/adjustment.model';
import { MovementsService } from './movements.service';
import { ProductsService } from './products.service';

interface StockAdjustmentDto {
  id: number;
  productId: number;
  productName: string;
  previousStock: number;
  newStock: number;
  quantityDelta: number;
  reason: string;
  date: string;
  createdBy: string;
}

function toAdjustment(dto: StockAdjustmentDto): StockAdjustment {
  return { ...dto, id: String(dto.id), productId: String(dto.productId) };
}

/** Ajustes al conteo físico (`POST /api/inventory/adjustments`, solo Administrador). */
@Injectable({ providedIn: 'root' })
export class AdjustmentsService {
  private readonly http = inject(HttpClient);
  private readonly movementsApi = inject(MovementsService);
  private readonly products = inject(ProductsService);
  private readonly baseUrl = `${environment.apiUrl}/inventory/adjustments`;

  #adjustments = signal<StockAdjustment[]>([]);
  readonly adjustments = this.#adjustments.asReadonly();

  /**
   * El historial de ajustes sale de los movimientos de tipo `ajuste`: el stock anterior es el
   * resultante menos la cantidad (que lleva signo).
   */
  getAdjustments(): Observable<StockAdjustment[]> {
    return this.movementsApi.getMovements('ajuste').pipe(
      map((movements) =>
        movements.map((m) => ({
          id: m.id,
          productId: m.productId,
          productName: m.productName,
          previousStock: Math.round((m.resultingStock - m.quantity) * 1000) / 1000,
          newStock: m.resultingStock,
          quantityDelta: m.quantity,
          reason: m.reference,
          date: m.date,
          createdBy: m.createdBy,
        })),
      ),
      tap((adjustments) => this.#adjustments.set(adjustments)),
    );
  }

  /** Fija el stock real del producto. Se envía el stock nuevo, no la diferencia. */
  createAdjustment(productId: string, newStock: number, reason: string): Observable<StockAdjustment> {
    return this.http
      .post<StockAdjustmentDto>(this.baseUrl, { productId: Number(productId), newStock, reason: reason.trim() })
      .pipe(
        map(toAdjustment),
        tap((adjustment) => {
          this.#adjustments.update((list) => [adjustment, ...list]);
          this.products.refresh();
        }),
      );
  }
}
