import { Component, booleanAttribute, input, output } from '@angular/core';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';
export type ButtonSize = 'sm' | 'md' | 'lg';

@Component({
  selector: 'app-button',
  imports: [],
  templateUrl: './button.html',
  styleUrl: './button.scss',
})
export class Button {
  variant = input<ButtonVariant>('primary');
  size = input<ButtonSize>('md');
  type = input<'button' | 'submit'>('button');
  loading = input(false, { transform: booleanAttribute });
  disabled = input(false, { transform: booleanAttribute });
  fullWidth = input(false, { transform: booleanAttribute });

  clicked = output<MouseEvent>();

  onClick(event: MouseEvent): void {
    if (this.disabled() || this.loading()) return;
    this.clicked.emit(event);
  }
}
