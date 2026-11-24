import { Injectable, computed, inject, signal } from '@angular/core';
import type { Session } from '@supabase/auth-js';
import { firstValueFrom } from 'rxjs';
import { LoginCredentials } from '../models/auth.model';
import { MeResponse } from '../models/company.model';
import { User } from '../models/user.model';
import { CompanyContextService } from './company-context.service';
import { MeApiService } from './me-api.service';
import { StorageService } from './storage.service';
import { SUPABASE_AUTH } from './supabase-auth.token';

export type AuthStatus =
  | 'loading'
  | 'unauthenticated'
  | 'authenticated'
  | 'no-company'
  | 'company-selection-required'
  | 'error';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly supabaseAuth = inject(SUPABASE_AUTH);
  private readonly meApi = inject(MeApiService);
  private readonly companyContext = inject(CompanyContextService);
  private readonly storage = inject(StorageService);

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

    let result;

    try {
      result = await this.supabaseAuth.signInWithPassword({
        email: credentials.email.trim().toLowerCase(),
        password: credentials.password,
      });
    } catch {
      this.#status.set('unauthenticated');
      throw new Error(
        'No se pudo conectar con el servicio de autenticación. Comprueba tu conexión e inténtalo nuevamente.',
      );
    }

    const { data, error } = result;

    if (error) {
      this.#status.set('unauthenticated');
      throw new Error(
        error.message === 'Invalid login credentials'
          ? 'Correo o contraseña incorrectos.'
          : error.message,
      );
    }

    if (!data.session) {
      this.#status.set('unauthenticated');
      throw new Error('Supabase no devolvió una sesión válida.');
    }

    this.#hasSession.set(true);
    await this.#loadCompanyContext(data.session);
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
      await this.supabaseAuth.signOut();
    } finally {
      this.#user.set(null);
      this.#hasSession.set(false);
      this.#status.set('unauthenticated');
      this.#initialization = null;
      this.#accountCreatedAt.set(null);
      this.companyContext.clear();
    }
  }

  defaultRouteForCurrentUser(): string {
    return this.currentUser()?.role === 'admin' ? '/dashboard' : '/sales';
  }

  async #restoreSession(): Promise<void> {
    this.#status.set('loading');

    const { data, error } = await this.supabaseAuth.getSession();

    if (error) throw error;

    if (!data.session) {
      this.#hasSession.set(false);
      this.#user.set(null);
      this.#accountCreatedAt.set(null);
      this.#status.set('unauthenticated');
      this.companyContext.clear();
      return;
    }

    this.#hasSession.set(true);
    await this.#loadCompanyContext(data.session);
  }

  async #loadCompanyContext(session: Session): Promise<void> {
    this.#status.set('loading');
    this.#user.set(null);
    this.#accountCreatedAt.set(session.user.created_at ?? null);

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

}
