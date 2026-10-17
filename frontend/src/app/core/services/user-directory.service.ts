import { Injectable, signal } from '@angular/core';
import { Observable } from 'rxjs';
import { User } from '../models/user.model';
import { USERS_MOCK } from '../../mocks/users.mock';
import { simulateRequest } from './mock-http.util';
import { generateId } from '../utils/id.util';
import { TENANT_ID } from '../../mocks/seed-ids.const';

export type NewUserInput = Pick<User, 'email' | 'fullName' | 'role'>;

/** Single source of truth for all app users — AuthService and the Settings > Usuarios CRUD both read/write here. */
@Injectable({ providedIn: 'root' })
export class UserDirectoryService {
  #users = signal<User[]>(USERS_MOCK);
  readonly users = this.#users.asReadonly();

  getUsers(): Observable<User[]> {
    return simulateRequest(this.#users());
  }

  findByEmail(email: string): User | undefined {
    return this.#users().find((u) => u.email.toLowerCase() === email.toLowerCase());
  }

  createUser(input: NewUserInput): Observable<User> {
    const user: User = {
      id: generateId(),
      email: input.email,
      fullName: input.fullName,
      role: input.role,
      tenantId: TENANT_ID,
      active: true,
      avatarInitials: initialsFor(input.fullName),
      createdAt: new Date().toISOString(),
    };
    this.#users.update((list) => [user, ...list]);
    return simulateRequest(user);
  }

  updateUser(id: string, changes: Partial<Pick<User, 'fullName' | 'role'>>): Observable<User> {
    this.#users.update((list) => list.map((u) => (u.id === id ? { ...u, ...changes } : u)));
    return simulateRequest(this.#users().find((u) => u.id === id)!);
  }

  setActive(id: string, active: boolean): Observable<User> {
    this.#users.update((list) => list.map((u) => (u.id === id ? { ...u, active } : u)));
    return simulateRequest(this.#users().find((u) => u.id === id)!);
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
