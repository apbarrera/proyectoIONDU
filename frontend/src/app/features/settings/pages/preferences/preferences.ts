import { Component, inject } from '@angular/core';
import { ThemeService, ThemePreference } from '../../../../core/services/theme.service';
import { PageHeader } from '../../../../shared/components/page-header/page-header';
import { Card } from '../../../../shared/components/card/card';
import { IconName } from '../../../../shared/icons/icons.generated';
import { Icon } from '../../../../shared/components/icon/icon';

const OPTIONS: { value: ThemePreference; label: string; icon: IconName }[] = [
  { value: 'light', label: 'Claro', icon: 'sun' },
  { value: 'dark', label: 'Oscuro', icon: 'moon' },
  { value: 'system', label: 'Sistema', icon: 'system' },
];

@Component({
  selector: 'app-preferences',
  imports: [PageHeader, Card, Icon],
  templateUrl: './preferences.html',
  styleUrl: './preferences.scss',
})
export class Preferences {
  themeService = inject(ThemeService);
  options = OPTIONS;
}
