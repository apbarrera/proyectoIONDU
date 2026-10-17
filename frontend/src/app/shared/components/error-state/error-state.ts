import { Component, input, output } from '@angular/core';
import { Button } from '../button/button';
import { Icon } from '../icon/icon';

@Component({
  selector: 'app-error-state',
  imports: [Button, Icon],
  templateUrl: './error-state.html',
  styleUrl: './error-state.scss',
})
export class ErrorState {
  title = input('No fue posible completar la acción.');
  description = input<string>();
  retryLabel = input('Reintentar');

  retry = output<void>();
}
