import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { AuthTokenResponse, LoginCredentials } from '../models/auth.model';

/**
 * Endpoints de sesión del backend (/api/auth). El token de renovación viaja en una
 * cookie httpOnly que el navegador envía solo; JavaScript nunca lo ve.
 */
@Injectable({ providedIn: 'root' })
export class AuthApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/auth`;

  login(credentials: LoginCredentials): Observable<AuthTokenResponse> {
    return this.http.post<AuthTokenResponse>(`${this.baseUrl}/login`, credentials, {
      withCredentials: true,
    });
  }

  refresh(): Observable<AuthTokenResponse> {
    return this.http.post<AuthTokenResponse>(`${this.baseUrl}/refresh`, null, {
      withCredentials: true,
    });
  }

  logout(): Observable<void> {
    return this.http.post<void>(`${this.baseUrl}/logout`, null, { withCredentials: true });
  }

  /** Cambia la contraseña del usuario de la sesión (exige el token de acceso). */
  changePassword(currentPassword: string, newPassword: string): Observable<AuthTokenResponse> {
    return this.http.post<AuthTokenResponse>(
      `${environment.apiUrl}/me/password`,
      { currentPassword, newPassword },
      { withCredentials: true },
    );
  }
}
