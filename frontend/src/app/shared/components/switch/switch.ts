import { Component, input, model } from '@angular/core';

/**
 * Interruptor accesible (role="switch"). Se maneja con ratón, Espacio y Enter, y anuncia
 * su estado a lectores de pantalla mediante aria-checked.
 */
@Component({
  selector: 'app-switch',
  templateUrl: './switch.html',
  styleUrl: './switch.scss',
})
export class Switch {
  checked = model(false);
  label = input.required<string>();
  description = input('');
  disabled = input(false);

  toggle(): void {
    if (!this.disabled()) this.checked.update((value) => !value);
  }
}
