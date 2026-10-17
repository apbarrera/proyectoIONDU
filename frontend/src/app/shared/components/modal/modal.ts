import { Component, HostListener, input, output } from '@angular/core';
import { Icon } from '../icon/icon';

@Component({
  selector: 'app-modal',
  imports: [Icon],
  templateUrl: './modal.html',
  styleUrl: './modal.scss',
})
export class Modal {
  open = input.required<boolean>();
  title = input<string>();
  size = input<'sm' | 'md' | 'lg'>('md');
  closeOnBackdrop = input(true);

  closed = output<void>();

  @HostListener('document:keydown.escape')
  onEscape(): void {
    if (this.open()) this.closed.emit();
  }

  onBackdropClick(): void {
    if (this.closeOnBackdrop()) this.closed.emit();
  }
}
