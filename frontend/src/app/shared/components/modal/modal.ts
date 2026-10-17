import { Component, ElementRef, HostListener, effect, inject, input, output } from '@angular/core';
import { Icon } from '../icon/icon';

let nextId = 0;

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

@Component({
  selector: 'app-modal',
  imports: [Icon],
  templateUrl: './modal.html',
  styleUrl: './modal.scss',
})
export class Modal {
  private host = inject<ElementRef<HTMLElement>>(ElementRef);
  private previouslyFocused: HTMLElement | null = null;

  open = input.required<boolean>();
  title = input<string>();
  size = input<'sm' | 'md' | 'lg'>('md');
  closeOnBackdrop = input(true);

  closed = output<void>();

  readonly titleId = `modal-title-${nextId++}`;

  constructor() {
    // Al abrir, el foco pasa al diálogo; al cerrar, vuelve al elemento que lo abrió.
    effect(() => {
      if (this.open()) {
        this.previouslyFocused = document.activeElement as HTMLElement | null;
        setTimeout(() => this.host.nativeElement.querySelector<HTMLElement>('.modal')?.focus());
      } else if (this.previouslyFocused) {
        this.previouslyFocused.focus();
        this.previouslyFocused = null;
      }
    });
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    if (this.open()) this.closed.emit();
  }

  /** Mantiene el foco dentro del diálogo mientras está abierto (Tab y Mayús+Tab). */
  onKeydown(event: KeyboardEvent): void {
    if (event.key !== 'Tab') return;
    const dialog = event.currentTarget as HTMLElement;
    const focusable = Array.from(dialog.querySelectorAll<HTMLElement>(FOCUSABLE));
    if (focusable.length === 0) {
      event.preventDefault();
      return;
    }
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    const active = document.activeElement;
    if (event.shiftKey && (active === first || active === dialog)) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && active === last) {
      event.preventDefault();
      first.focus();
    }
  }

  onBackdropClick(): void {
    if (this.closeOnBackdrop()) this.closed.emit();
  }
}
