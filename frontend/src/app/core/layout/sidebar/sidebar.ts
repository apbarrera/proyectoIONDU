import { Component, computed, inject, input, output } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { NAV_ITEMS, NavItem } from './nav-items.const';

@Component({
  selector: 'app-sidebar',
  imports: [RouterLink, RouterLinkActive],
  templateUrl: './sidebar.html',
  styleUrl: './sidebar.scss',
})
export class Sidebar {
  private auth = inject(AuthService);

  mobileOpen = input(false);
  linkClicked = output<void>();

  visibleItems = computed<NavItem[]>(() => {
    const role = this.auth.currentUser()?.role;
    if (!role) return [];
    return NAV_ITEMS.filter((item) => item.roles.includes(role)).map((item) => ({
      ...item,
      children: item.children?.filter((child) => !child.roles || child.roles.includes(role)),
    }));
  });

  onLinkClick(): void {
    this.linkClicked.emit();
  }
}
