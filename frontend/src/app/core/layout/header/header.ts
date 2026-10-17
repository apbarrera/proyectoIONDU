import { Component, inject, output, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { ToastService } from '../../services/toast.service';

@Component({
  selector: 'app-header',
  imports: [RouterLink],
  templateUrl: './header.html',
  styleUrl: './header.scss',
})
export class Header {
  private auth = inject(AuthService);
  private router = inject(Router);
  private toast = inject(ToastService);

  menuToggled = output<void>();
  currentUser = this.auth.currentUser;
  profileMenuOpen = signal(false);

  toggleProfileMenu(): void {
    this.profileMenuOpen.update((v) => !v);
  }

  logout(): void {
    this.profileMenuOpen.set(false);
    this.auth.logout();
    this.toast.info('Sesión cerrada.');
    this.router.navigateByUrl('/login');
  }
}
