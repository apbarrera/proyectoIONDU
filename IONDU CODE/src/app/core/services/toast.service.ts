import { Injectable, signal } from '@angular/core';
import { Toast, ToastType } from '../models/toast.model';
import { generateId } from '../utils/id.util';

@Injectable({ providedIn: 'root' })
export class ToastService {
  #toasts = signal<Toast[]>([]);
  readonly toasts = this.#toasts.asReadonly();

  show(message: string, type: ToastType = 'info', duration = 4500): void {
    const toast: Toast = { id: generateId(), type, message, duration };
    this.#toasts.update((list) => [...list, toast].slice(-3));
    setTimeout(() => this.dismiss(toast.id), duration);
  }

  success(message: string): void {
    this.show(message, 'success');
  }

  error(message: string): void {
    this.show(message, 'error', 6000);
  }

  info(message: string): void {
    this.show(message, 'info');
  }

  warning(message: string): void {
    this.show(message, 'warning', 5500);
  }

  dismiss(id: string): void {
    this.#toasts.update((list) => list.filter((t) => t.id !== id));
  }
}
