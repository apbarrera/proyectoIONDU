import { HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { AuthTokenResponse } from '../models/auth.model';
import { AuthApiService } from './auth-api.service';

/** Se renueva un poco antes de que venza para no enviar peticiones con un token caducado. */
const MARGEN_RENOVACION_MS = 30_000;

/**
 * Guarda el token de acceso SOLO en memoria (no en localStorage): un script inyectado
 * no puede leerlo de ahí y al cerrar la pestaña desaparece. La sesión se recupera con
 * la cookie httpOnly de renovación.
 */
@Injectable({ providedIn: 'root' })
export class AuthTokenService {
  private readonly api = inject(AuthApiService);

  #token: string | null = null;
  #expiresAt = 0;
  #refreshing: Promise<AuthTokenResponse | null> | null = null;

  get accessToken(): string | null {
    return this.#token;
  }

  set(response: AuthTokenResponse, now = Date.now()): void {
    this.#token = response.accessToken;
    this.#expiresAt = now + response.expiresIn * 1000;
  }

  clear(): void {
    this.#token = null;
    this.#expiresAt = 0;
  }

  isExpiringSoon(now = Date.now()): boolean {
    return this.#token !== null && now >= this.#expiresAt - MARGEN_RENOVACION_MS;
  }

  /**
   * Pide un token nuevo con la cookie de renovación. Varias peticiones simultáneas
   * comparten la misma renovación. Devuelve null si la sesión ya no es válida (401);
   * cualquier otro error (red, servidor) se propaga.
   */
  refresh(): Promise<AuthTokenResponse | null> {
    this.#refreshing ??= this.#doRefresh().finally(() => {
      this.#refreshing = null;
    });
    return this.#refreshing;
  }

  async #doRefresh(): Promise<AuthTokenResponse | null> {
    try {
      const response = await firstValueFrom(this.api.refresh());
      this.set(response);
      return response;
    } catch (error) {
      if (error instanceof HttpErrorResponse && error.status === 401) {
        this.clear();
        return null;
      }
      throw error;
    }
  }
}
