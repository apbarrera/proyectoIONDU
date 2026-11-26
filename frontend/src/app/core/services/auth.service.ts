import { HttpErrorResponse } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { AuthTokenResponse, LoginCredentials } from '../models/auth.model';
import { MeResponse } from '../models/company.model';
import { User } from '../models/user.model';
import { CompanyContextService } from './company-context.service';
import { AuthApiService } from './auth-api.service';
import { AuthTokenService } from './auth-token.service';
import { MeApiService } from './me-api.service';

export type AuthStatus =
  | 'loading'
  | 'unauthenticated'
  | 'authenticated'
  | 'no-company'
  | 'company-selection-required'
  | 'error';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly authApi = inject(AuthApiService);
  private readonly tokens = inject(AuthTokenService);
  private readonly meApi = inject(MeApiService);
  private readonly companyContext = inject(CompanyContextService);

  #user = signal<User | null>(null);
  #hasSession = signal(false);
  #status = signal<AuthStatus>('loading');
  #initialization: Promise<void> | null = null;
  #accountCreatedAt = signal<string | null>(null);

  readonly currentUser = this.#user.asReadonly();
  readonly status = this.#status.asReadonly();
  readonly isAuthenticated = computed(() => this.#hasSession());
  readonly isAdmin = computed(() => this.currentUser()?.role === 'admin');

  initialize(): Promise<void> {
    if (this.#initialization) return this.#initialization;

    this.#initialization = this.#restoreSession().catch((error: unknown) => {
      this.#status.set('error');
      this.#initialization = null;
      throw error;
    });

    return this.#initialization;
  }

  async login(credentials: LoginCredentials): Promise<void> {
    this.#initialization = null;
    this.#status.set('loading');
    this.#user.set(null);
    this.#hasSession.set(false);
    this.#accountCreatedAt.set(null);

    let session: AuthTokenResponse;

    try {
      session = await firstValueFrom(
        this.authApi.login({
          email: credentials.email.trim().toLowerCase(),
          password: credentials.password,
        }),
      );
    } catch (error) {
      this.#status.set('unauthenticated');
      throw new Error(this.#loginErrorMessage(error));
    }

    this.tokens.set(session);
    this.#hasSession.set(true);
    await this.#loadCompanyContext(session);
    // La sesión ya está cargada: los guards no necesitan renovarla otra vez.
    this.#initialization = Promise.resolve();
  }

  async selectCompany(companyId: number): Promise<void> {
    if (!this.#hasSession()) {
      throw new Error('Debes iniciar sesión para seleccionar una empresa.');
    }

    if (!this.companyContext.selectCompany(companyId)) {
      throw new Error('No tienes acceso a la empresa seleccionada.');
    }

    this.#status.set('loading');
    this.#user.set(null);

    try {
      await this.#loadProfile();
    } catch (error) {
      this.#status.set('error');
      throw error;
    }
  }

  async logout(): Promise<void> {
    try {
      await firstValueFrom(this.authApi.logout());
    } catch {
      // Sin conexión la cookie no se revoca en el servidor, pero la sesión local se cierra igual.
    } finally {
      this.#resetSession();
    }
  }

  /**
   * Cambia la contraseña. El servidor cierra las demás sesiones y entrega una nueva
   * para este navegador, que reemplaza al token actual.
   */
  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    const session = await firstValueFrom(
      this.authApi.changePassword(currentPassword, newPassword),
    );
    this.tokens.set(session);
  }

  /** La sesión venció y no se pudo renovar (lo detecta el interceptor). */
  handleSessionExpired(): void {
    this.#resetSession();
  }

  defaultRouteForCurrentUser(): string {
    return this.currentUser()?.role === 'admin' ? '/dashboard' : '/sales';
  }

  async #restoreSession(): Promise<void> {
    this.#status.set('loading');

    // Al recargar la página el token en memoria se perdió: se recupera con la cookie.
    const session = await this.tokens.refresh();

    if (!session) {
      this.#resetSession();
      return;
    }

    this.#hasSession.set(true);
    await this.#loadCompanyContext(session);
  }

  async #loadCompanyContext(session: AuthTokenResponse): Promise<void> {
    this.#status.set('loading');
    this.#user.set(null);
    this.#accountCreatedAt.set(session.user.createdAt ?? null);

    try {
      const companies = await firstValueFrom(this.meApi.getCompanies());
      this.companyContext.setCompanies(companies);

      if (companies.length === 0) {
        this.companyContext.clear();
        this.#status.set('no-company');
        return;
      }

      if (this.companyContext.selectedCompanyId() === null) {
        this.#status.set('company-selection-required');
        return;
      }

      await this.#loadProfile();
    } catch (error) {
      this.#status.set('error');
      throw error;
    }
  }

  async #loadProfile(): Promise<void> {
    const selectedCompanyId = this.companyContext.selectedCompanyId();

    if (selectedCompanyId === null) {
      this.#status.set('company-selection-required');
      return;
    }

    const profile = await firstValueFrom(this.meApi.getMe());

    if (profile.tenantId !== selectedCompanyId) {
      throw new Error('El perfil recibido no corresponde a la empresa seleccionada.');
    }

    if (!profile.active) {
      throw new Error('El usuario no tiene una membresía activa en esta empresa.');
    }

    this.#user.set(this.#mapUser(profile));
    this.#status.set('authenticated');
  }

  #mapUser(profile: MeResponse): User {
    const fullName = profile.fullName.trim();
    const initials = fullName
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part.charAt(0).toUpperCase())
      .join('');

    return {
      id: profile.id,
      email: profile.email ?? '',
      fullName,
      role: profile.role,
      tenantId: String(profile.tenantId),
      active: profile.active,
      avatarInitials: initials,
      createdAt: this.#accountCreatedAt() ?? '',
    };
  }

  #resetSession(): void {
    this.tokens.clear();
    this.#user.set(null);
    this.#hasSession.set(false);
    this.#status.set('unauthenticated');
    this.#initialization = null;
    this.#accountCreatedAt.set(null);
    this.companyContext.clear();
  }

  #loginErrorMessage(error: unknown): string {
    if (!(error instanceof HttpErrorResponse) || error.status === 0) {
      return 'No se pudo conectar con el servicio de autenticación. Comprueba tu conexión e inténtalo nuevamente.';
    }
    const message: unknown = error.error?.error?.message;
    if ((error.status === 401 || error.status === 429) && typeof message === 'string') {
      return message;
    }
    if (error.status === 401) return 'Correo o contraseña incorrectos.';
    return 'No se pudo iniciar sesión. Inténtalo nuevamente en unos minutos.';
  }
}
