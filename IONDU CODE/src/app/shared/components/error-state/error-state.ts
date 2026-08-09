import { Component, input, output } from '@angular/core';
import { Button } from '../button/button';

@Component({
  selector: 'app-error-state',
  imports: [Button],
  templateUrl: './error-state.html',
  styleUrl: './error-state.scss',
})
export class ErrorState {
  title = input('No fue posible completar la acción.');
  description = input<string>();
  retryLabel = input('Reintentar');

  retry = output<void>();
}
