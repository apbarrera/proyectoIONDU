export type UserRole = 'admin' | 'operator';

export interface User {
  id: string;
  email: string;
  fullName: string;
  role: UserRole;
  tenantId: string;
  active: boolean;
  avatarInitials: string;
  createdAt: string;
}
