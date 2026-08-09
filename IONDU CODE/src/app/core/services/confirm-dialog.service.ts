import { Injectable, signal } from '@angular/core';
import { Observable } from 'rxjs';

export interface ConfirmDialogRequest {
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  danger?: boolean;
}

interface ActiveConfirm extends ConfirmDialogRequest {
  resolve: (value: boolean) => void;
}

@Injectable({ providedIn: 'root' })
export class ConfirmDialogService {
  #active = signal<ActiveConfirm | null>(null);
  readonly active = this.#active.asReadonly();

  confirm(request: ConfirmDialogRequest): Observable<boolean> {
    return new Observable<boolean>((subscriber) => {
      this.#active.set({
        ...request,
        resolve: (value) => {
          subscriber.next(value);
          subscriber.complete();
        },
      });
    });
  }

  resolve(value: boolean): void {
    this.#active()?.resolve(value);
    this.#active.set(null);
  }
}
