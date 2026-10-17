import { Component, computed, inject, output, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { Icon } from '../../../shared/components/icon/icon';
import { IconName } from '../../../shared/icons/icons.generated';
import { AuthService } from '../../services/auth.service';
import { ThemePreference, ThemeService } from '../../services/theme.service';
import { ToastService } from '../../services/toast.service';

const THEME_CYCLE: ThemePreference[] = ['system', 'light', 'dark'];

const THEME_META: Record<ThemePreference, { icon: IconName; label: string }> = {
  system: { icon: 'system', label: 'Tema del sistema' },
  light: { icon: 'sun', label: 'Tema claro' },
  dark: { icon: 'moon', label: 'Tema oscuro' },
};

@Component({
  selector: 'app-header',
  imports: [RouterLink, Icon],
  templateUrl: './header.html',
  styleUrl: './header.scss',
})
export class Header {
  private auth = inject(AuthService);
  private router = inject(Router);
  private toast = inject(ToastService);
  private theme = inject(ThemeService);

  menuToggled = output<void>();
  currentUser = this.auth.currentUser;
  profileMenuOpen = signal(false);

  themeMeta = computed(() => THEME_META[this.theme.preference()]);
  nextThemeLabel = computed(() => {
    const next = this.#nextTheme();
    return `Cambiar a ${THEME_META[next].label.toLowerCase()}`;
  });

  toggleProfileMenu(): void {
    this.profileMenuOpen.update((v) => !v);
  }

  cycleTheme(): void {
    this.theme.setPreference(this.#nextTheme());
  }

  logout(): void {
    this.profileMenuOpen.set(false);
    this.auth.logout();
    this.toast.info('Sesión cerrada.');
    this.router.navigateByUrl('/login');
  }

  #nextTheme(): ThemePreference {
    const index = THEME_CYCLE.indexOf(this.theme.preference());
    return THEME_CYCLE[(index + 1) % THEME_CYCLE.length];
  }
}
