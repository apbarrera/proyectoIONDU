import { Component, computed, inject, input } from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { ICONS, IconName } from '../../icons/icons.generated';

/**
 * Ícono SVG inline (Phosphor). Hereda el color del texto (currentColor) y escala con
 * `size`. Si el ícono es decorativo se oculta a lectores de pantalla; si lleva `label`,
 * se expone como imagen con ese nombre.
 */
@Component({
  selector: 'app-icon',
  templateUrl: './icon.html',
  styleUrl: './icon.scss',
  host: {
    '[style.--icon-size.px]': 'size()',
    '[attr.role]': 'label() ? "img" : null',
    '[attr.aria-label]': 'label() || null',
    '[attr.aria-hidden]': 'label() ? null : "true"',
  },
})
export class Icon {
  private sanitizer = inject(DomSanitizer);

  name = input.required<IconName>();
  size = input(20);
  label = input('');

  // El contenido sale del registro generado en build (ICONS), nunca de entrada de usuario.
  markup = computed<SafeHtml>(() =>
    this.sanitizer.bypassSecurityTrustHtml(
      `<svg viewBox="0 0 256 256" fill="currentColor" focusable="false">${ICONS[this.name()]}</svg>`,
    ),
  );
}
