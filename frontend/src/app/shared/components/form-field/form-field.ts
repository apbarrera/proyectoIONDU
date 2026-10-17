import { Component, ElementRef, afterNextRender, booleanAttribute, effect, inject, input, signal } from '@angular/core';

let nextId = 0;

/**
 * Etiqueta, ayuda y error de un campo. Vincula la etiqueta con el campo proyectado
 * (`for`/`id`) y expone el error o la ayuda a lectores de pantalla (`aria-describedby`).
 */
@Component({
  selector: 'app-form-field',
  imports: [],
  templateUrl: './form-field.html',
  styleUrl: './form-field.scss',
})
export class FormField {
  private host = inject<ElementRef<HTMLElement>>(ElementRef);
  private uid = nextId++;

  label = input<string>();
  hint = input<string>();
  error = input<string | null>(null);
  required = input(false, { transform: booleanAttribute });

  readonly messageId = `form-field-message-${this.uid}`;
  labelFor = signal(`form-field-control-${this.uid}`);
  private control = signal<HTMLElement | null>(null);

  constructor() {
    afterNextRender(() => {
      const control = this.host.nativeElement.querySelector<HTMLElement>('input, select, textarea');
      if (!control) return;
      if (!control.id) control.id = this.labelFor();
      this.labelFor.set(control.id);
      this.control.set(control);
    });

    effect(() => {
      const control = this.control();
      if (!control) return;
      const hasMessage = !!this.error() || !!this.hint();
      control.setAttribute('aria-invalid', String(!!this.error()));
      if (hasMessage) control.setAttribute('aria-describedby', this.messageId);
      else control.removeAttribute('aria-describedby');
    });
  }
}
