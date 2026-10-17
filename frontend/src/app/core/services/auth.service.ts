import { Injectable, computed, inject, signal } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { tap } from 'rxjs/operators';
import { AuthSession, LoginCredentials } from '../models/auth.model';
import { User } from '../models/user.model';
import { DEMO_PASSWORD } from '../../mocks/users.mock';
import { StorageService } from './storage.service';
import { UserDirectoryService } from './user-directory.service';
import { generateId } from '../utils/id.util';
import { simulateRequest } from './mock-http.util';

const STORAGE_KEY = 'iondu-session';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private storage = inject(StorageService);
  private userDirectory = inject(UserDirectoryService);

  #session = signal<AuthSession | null>(this.storage.get<AuthSession>(STORAGE_KEY));

  readonly currentUser = computed<User | null>(() => this.#session()?.user ?? null);
  readonly isAuthenticated = computed(() => !!this.#session());
  readonly isAdmin = computed(() => this.currentUser()?.role === 'admin');

  login(credentials: LoginCredentials): Observable<AuthSession> {
    const user = this.userDirectory.findByEmail(credentials.email.trim());

    if (!user || !user.active || credentials.password !== DEMO_PASSWORD) {
      return throwError(() => new Error('Correo o contraseña incorrectos.'));
    }

    const session: AuthSession = {
      user,
      token: generateId(),
      expiresAt: new Date(Date.now() + 1000 * 60 * 60 * 8).toISOString(),
    };

    return simulateRequest(session).pipe(
      tap((s) => {
        this.#session.set(s);
        if (credentials.rememberSession) {
          this.storage.set(STORAGE_KEY, s);
        }
      }),
    );
  }

  logout(): void {
    this.#session.set(null);
    this.storage.remove(STORAGE_KEY);
  }

  defaultRouteForCurrentUser(): string {
    return this.currentUser()?.role === 'admin' ? '/dashboard' : '/sales';
  }
}
