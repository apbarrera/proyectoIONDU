import { Injectable, inject, signal } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, map, tap } from 'rxjs';

import { environment } from '../../../../environments/environment';
import { fetchAllPages } from '../../../core/utils/pagination.util';
import { BackendMovementType, InventoryMovement } from '../models/movement.model';

export interface MovementDto {
  id: number;
  productId: number;
  productName: string;
  unit: string;
  type: BackendMovementType;
  quantity: number;
  resultingStock: number;
  reason: string;
  date: string;
  createdBy: string;
}

export function toMovement(dto: MovementDto): InventoryMovement {
  return {
    id: String(dto.id),
    productId: String(dto.productId),
    productName: dto.productName,
    unit: dto.unit,
    type: dto.type,
    quantity: dto.quantity,
    resultingStock: dto.resultingStock,
    reference: dto.reason,
    date: dto.date,
    createdBy: dto.createdBy,
  };
}

export interface ManualMovementInput {
  productId: number;
  type: 'entrada' | 'salida';
  quantity: number;
  reason: string;
}

/** Historial de movimientos y entradas/salidas manuales (`/api/inventory/movements`). */
@Injectable({ providedIn: 'root' })
export class MovementsService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/inventory/movements`;

  #movements = signal<InventoryMovement[]>([]);
  readonly movements = this.#movements.asReadonly();

  /** Descarga todo el historial (el más reciente primero) y actualiza `movements`. */
  getMovements(type?: BackendMovementType): Observable<InventoryMovement[]> {
    return fetchAllPages<MovementDto>((page) => {
      let params = new HttpParams().set('page', page).set('pageSize', 100);
      if (type) params = params.set('type', type);
      return this.http.get<{ items: MovementDto[]; total: number; page: number; pageSize: number }>(this.baseUrl, {
        params,
      });
    }).pipe(
      map((items) => items.map(toMovement)),
      tap((movements) => {
        if (!type) this.#movements.set(movements);
      }),
    );
  }

  /** Entrada o salida manual (RF-4.3). El backend actualiza el stock en la misma transacción. */
  record(input: ManualMovementInput): Observable<InventoryMovement> {
    return this.http.post<MovementDto>(this.baseUrl, input).pipe(
      map(toMovement),
      tap((movement) => this.#movements.update((list) => [movement, ...list])),
    );
  }
}
