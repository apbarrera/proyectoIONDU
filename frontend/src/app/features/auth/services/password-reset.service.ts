import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';
import { environment } from '../../../../environments/environment';

/** Recuperación de contraseña por correo (enlaces de un solo uso). No requiere sesión. */
@Injectable({ providedIn: 'root' })
export class PasswordResetService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/auth/password-reset`;

  /** Responde lo mismo exista o no el correo; devuelve el mensaje para mostrar. */
  request(email: string): Observable<string> {
    return this.http
      .post<{ message: string }>(this.baseUrl, { email: email.trim() })
      .pipe(map((response) => response.message));
  }

  confirm(token: string, newPassword: string): Observable<void> {
    return this.http.post<void>(`${this.baseUrl}/confirm`, { token, newPassword });
  }
}
