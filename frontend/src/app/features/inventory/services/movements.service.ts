import { Injectable, signal } from '@angular/core';
import { Observable } from 'rxjs';
import { InventoryMovement, MovementType } from '../models/movement.model';
import { INVENTORY_MOVEMENTS_MOCK } from '../../../mocks/inventory-movements.mock';
import { simulateRequest } from '../../../core/services/mock-http.util';
import { generateId } from '../../../core/utils/id.util';

@Injectable({ providedIn: 'root' })
export class MovementsService {
  #movements = signal<InventoryMovement[]>(INVENTORY_MOVEMENTS_MOCK);
  readonly movements = this.#movements.asReadonly();

  getMovements(): Observable<InventoryMovement[]> {
    return simulateRequest(this.#movements());
  }

  record(params: {
    productId: string;
    productName: string;
    type: MovementType;
    quantity: number;
    resultingStock: number;
    reference: string;
    createdBy: string;
  }): InventoryMovement {
    const movement: InventoryMovement = {
      id: generateId(),
      date: new Date().toISOString(),
      ...params,
    };
    this.#movements.update((list) => [movement, ...list]);
    return movement;
  }
}
