import { Component, input } from '@angular/core';
import { LOGO_PATH, LOGO_VIEWBOX } from './logo-mark.const';

/**
 * Isotipo de IONDU como SVG en línea. Usa `currentColor`, así que cambia solo entre tema
 * claro (tinta oscura) y tema oscuro (blanco) heredando el color del texto que lo rodea.
 */
@Component({
  selector: 'app-logo',
  templateUrl: './logo.html',
  styleUrl: './logo.scss',
  host: {
    '[style.--logo-size.px]': 'size()',
    role: 'img',
    'aria-label': 'IONDU',
  },
})
export class Logo {
  size = input(32);

  readonly viewBox = LOGO_VIEWBOX;
  readonly path = LOGO_PATH;
}
