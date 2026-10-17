import { Component, HostListener, computed, effect, inject, input, output, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { NavigationEnd, Router, RouterLink, RouterLinkActive } from '@angular/router';
import { filter, map, startWith } from 'rxjs';
import { Icon } from '../../../shared/components/icon/icon';
import { Logo } from '../../../shared/components/logo/logo';
import { AuthService } from '../../services/auth.service';
import { StorageService } from '../../services/storage.service';
import { NAV_ITEMS, NavItem } from './nav-items.const';

const STORAGE_KEY = 'iondu-sidebar';
export const SIDEBAR_MIN = 220;
export const SIDEBAR_MAX = 360;
export const SIDEBAR_DEFAULT = 264;
export const SIDEBAR_COLLAPSED = 72;
const KEY_STEP = 16;

interface SidebarPrefs {
  collapsed: boolean;
  width: number;
  /** Enlaces de los grupos que el usuario dejó abiertos. */
  open?: string[];
}

const clampWidth = (value: number): number => Math.min(SIDEBAR_MAX, Math.max(SIDEBAR_MIN, value));

@Component({
  selector: 'app-sidebar',
  imports: [RouterLink, RouterLinkActive, Icon, Logo],
  templateUrl: './sidebar.html',
  styleUrl: './sidebar.scss',
  host: {
    '[style.width.px]': 'hostWidth()',
    '[class.is-collapsed]': 'collapsed()',
    '[class.is-resizing]': 'resizing()',
  },
})
export class Sidebar {
  private auth = inject(AuthService);
  private router = inject(Router);
  private storage = inject(StorageService);

  mobileOpen = input(false);
  linkClicked = output<void>();

  private prefs = this.storage.get<SidebarPrefs>(STORAGE_KEY);
  collapsed = signal(this.prefs?.collapsed ?? false);
  width = signal(clampWidth(this.prefs?.width ?? SIDEBAR_DEFAULT));
  resizing = signal(false);
  /** Los grupos son independientes: se pueden dejar varios abiertos a la vez. */
  openGroups = signal<string[]>(this.prefs?.open ?? []);

  hostWidth = computed(() => (this.collapsed() ? SIDEBAR_COLLAPSED : this.width()));

  // En tablet y móvil el menú es un cajón fuera de pantalla: mientras está cerrado se marca
  // como inerte para que no reciba foco con el teclado ni aparezca para lectores de pantalla.
  #mobileMedia = window.matchMedia('(max-width: 1024px)');
  isMobile = signal(this.#mobileMedia.matches);
  inertWhenClosed = computed(() => this.isMobile() && !this.mobileOpen());

  readonly min = SIDEBAR_MIN;
  readonly max = SIDEBAR_MAX;

  private currentUrl = toSignal(
    this.router.events.pipe(
      filter((e): e is NavigationEnd => e instanceof NavigationEnd),
      map((e) => e.urlAfterRedirects),
      startWith(this.router.url),
    ),
    { initialValue: this.router.url },
  );

  visibleItems = computed<NavItem[]>(() => {
    const role = this.auth.currentUser()?.role;
    if (!role) return [];
    return NAV_ITEMS.filter((item) => item.roles.includes(role)).map((item) => ({
      ...item,
      children: item.children?.filter((child) => !child.roles || child.roles.includes(role)),
    }));
  });

  constructor() {
    this.#mobileMedia.addEventListener('change', (e) => this.isMobile.set(e.matches));

    // Al navegar se abre el grupo de la ruta actual, sin cerrar los que ya estaban abiertos.
    effect(() => {
      const url = this.currentUrl();
      const group = this.visibleItems().find(
        (item) => item.children?.length && url.startsWith(this.sectionOf(item)),
      );
      if (group) {
        this.openGroups.update((open) => (open.includes(group.link) ? open : [...open, group.link]));
      }
    });

    effect(() => {
      this.storage.set<SidebarPrefs>(STORAGE_KEY, {
        collapsed: this.collapsed(),
        width: this.width(),
        open: this.openGroups(),
      });
    });
  }

  isOpen(item: NavItem): boolean {
    return !this.collapsed() && this.openGroups().includes(item.link);
  }

  toggleGroup(item: NavItem): void {
    this.openGroups.update((open) =>
      open.includes(item.link) ? open.filter((link) => link !== item.link) : [...open, item.link],
    );
  }

  toggleCollapsed(): void {
    this.collapsed.update((v) => !v);
  }

  onLinkClick(): void {
    this.linkClicked.emit();
  }

  /** Con el cajón abierto, Escape lo cierra. */
  @HostListener('document:keydown.escape')
  onEscape(): void {
    if (this.isMobile() && this.mobileOpen()) this.linkClicked.emit();
  }

  // ---- Redimensionado: arrastrar el borde derecho o usar el teclado ----
  private dragStartX = 0;
  private dragStartWidth = 0;

  onResizeStart(event: PointerEvent): void {
    (event.target as HTMLElement).setPointerCapture(event.pointerId);
    this.dragStartX = event.clientX;
    this.dragStartWidth = this.width();
    this.resizing.set(true);
  }

  onResizeMove(event: PointerEvent): void {
    if (!this.resizing()) return;
    this.width.set(clampWidth(this.dragStartWidth + event.clientX - this.dragStartX));
  }

  onResizeEnd(): void {
    this.resizing.set(false);
  }

  onResizeKey(event: KeyboardEvent): void {
    const actions: Record<string, () => number> = {
      ArrowLeft: () => this.width() - KEY_STEP,
      ArrowRight: () => this.width() + KEY_STEP,
      Home: () => SIDEBAR_MIN,
      End: () => SIDEBAR_MAX,
      Enter: () => SIDEBAR_DEFAULT,
    };
    const next = actions[event.key];
    if (!next) return;
    event.preventDefault();
    this.width.set(clampWidth(next()));
  }

  resetWidth(): void {
    this.width.set(SIDEBAR_DEFAULT);
  }

  /** Primer segmento de la ruta de la sección: "/inventory/products" -> "/inventory". */
  private sectionOf(item: NavItem): string {
    return `/${item.link.split('/')[1]}`;
  }
}
