import { Component, input } from '@angular/core';

@Component({
  selector: 'app-loader',
  imports: [],
  templateUrl: './loader.html',
  styleUrl: './loader.scss',
})
export class Loader {
  label = input<string>('Cargando…');
  size = input<'sm' | 'md' | 'lg'>('md');
  inline = input(false);
}
