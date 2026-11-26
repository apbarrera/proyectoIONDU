import { HttpClient } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';
import { Observable, map, tap } from 'rxjs';
import { environment } from '../../../environments/environment';
import { User, UserRole } from '../models/user.model';
import { CompanyContextService } from './company-context.service';

export type NewUserInput = Pick<User, 'email' | 'fullName' | 'role'>;

/** Usuario de la empresa tal como lo devuelve GET /api/users. */
interface CompanyUserDto {
  id: string;
  email: string;
  fullName: string;
  role: UserRole;
  active: boolean;
  createdAt: string;
}

export interface CreatedUser {
  user: User;
  /** Solo si se creó una cuenta nueva; se muestra una sola vez. */
  temporaryPassword: string | null;
  /** Se envió por correo un enlace para que la persona elija su contraseña. */
  invitationSent: boolean;
}

/** Usuarios de la empresa seleccionada (solo Administrador): /api/users. */
@Injectable({ providedIn: 'root' })
export class UserDirectoryService {
  private readonly http = inject(HttpClient);
  private readonly companyContext = inject(CompanyContextService);
  private readonly baseUrl = `${environment.apiUrl}/users`;

  #users = signal<User[]>([]);
  readonly users = this.#users.asReadonly();

  load(): Observable<User[]> {
    return this.http.get<CompanyUserDto[]>(this.baseUrl).pipe(
      map((list) => list.map((dto) => this.#toUser(dto))),
      tap((users) => this.#users.set(users)),
    );
  }

  createUser(input: NewUserInput): Observable<CreatedUser> {
    return this.http
      .post<{ user: CompanyUserDto; temporaryPassword: string | null; invitationSent?: boolean }>(
        this.baseUrl,
        input,
      )
      .pipe(
        map((response) => ({
          user: this.#toUser(response.user),
          temporaryPassword: response.temporaryPassword,
          invitationSent: response.invitationSent ?? false,
        })),
        tap(({ user }) => this.#upsert(user)),
      );
  }

  updateUser(id: string, changes: Partial<Pick<User, 'fullName' | 'role'>>): Observable<User> {
    return this.#patch(id, changes);
  }

  setActive(id: string, active: boolean): Observable<User> {
    return this.#patch(id, { active });
  }

  /** Genera una contraseña temporal nueva y cierra las sesiones abiertas del usuario. */
  resetPassword(id: string): Observable<string> {
    return this.http
      .post<{ temporaryPassword: string }>(`${this.baseUrl}/${id}/reset-password`, null)
      .pipe(map((response) => response.temporaryPassword));
  }

  #patch(id: string, body: Partial<Pick<User, 'fullName' | 'role' | 'active'>>): Observable<User> {
    return this.http.patch<CompanyUserDto>(`${this.baseUrl}/${id}`, body).pipe(
      map((dto) => this.#toUser(dto)),
      tap((user) => this.#upsert(user)),
    );
  }

  #upsert(user: User): void {
    this.#users.update((list) =>
      list.some((u) => u.id === user.id)
        ? list.map((u) => (u.id === user.id ? user : u))
        : [user, ...list],
    );
  }

  #toUser(dto: CompanyUserDto): User {
    return {
      id: dto.id,
      email: dto.email,
      fullName: dto.fullName,
      role: dto.role,
      tenantId: String(this.companyContext.selectedCompanyId() ?? ''),
      active: dto.active,
      avatarInitials: initialsFor(dto.fullName),
      createdAt: dto.createdAt,
    };
  }
}

function initialsFor(fullName: string): string {
  return fullName
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join('');
}
