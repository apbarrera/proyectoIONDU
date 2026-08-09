import { User } from '../core/models/user.model';
import { TENANT_ID, USER_IDS } from './seed-ids.const';

export const USERS_MOCK: User[] = [
  {
    id: USER_IDS.ADMIN,
    email: 'admin@iondu.demo',
    fullName: 'María Fernanda Salazar',
    role: 'admin',
    tenantId: TENANT_ID,
    active: true,
    avatarInitials: 'MS',
    createdAt: '2025-01-10T08:00:00.000Z',
  },
  {
    id: USER_IDS.OPERATOR,
    email: 'operador@iondu.demo',
    fullName: 'Juan Carlos Pérez',
    role: 'operator',
    tenantId: TENANT_ID,
    active: true,
    avatarInitials: 'JP',
    createdAt: '2025-02-04T08:00:00.000Z',
  },
];

/** Demo password shared by both mock users — this is a mock-only login, never real auth. */
export const DEMO_PASSWORD = 'iondu2026';
