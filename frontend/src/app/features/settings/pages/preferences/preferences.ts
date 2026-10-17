import { Component, inject } from '@angular/core';
import { ThemeService, ThemePreference } from '../../../../core/services/theme.service';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { Card } from '../../../../shared/components/card/card';

const OPTIONS: { value: ThemePreference; label: string; icon: string }[] = [
  { value: 'light', label: 'Claro', icon: '☀️' },
  { value: 'dark', label: 'Oscuro', icon: '🌙' },
  { value: 'system', label: 'Sistema', icon: '🖥️' },
];

@Component({
  selector: 'app-preferences',
  imports: [PageHeader, Card],
  templateUrl: './preferences.html',
  styleUrl: './preferences.scss',
})
export class Preferences {
  themeService = inject(ThemeService);
  options = OPTIONS;
}
