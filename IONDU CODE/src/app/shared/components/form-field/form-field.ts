import { Component, booleanAttribute, input } from '@angular/core';

@Component({
  selector: 'app-form-field',
  imports: [],
  templateUrl: './form-field.html',
  styleUrl: './form-field.scss',
})
export class FormField {
  label = input<string>();
  hint = input<string>();
  error = input<string | null>(null);
  required = input(false, { transform: booleanAttribute });
}
