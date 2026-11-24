import { UserRole } from './user.model';

export interface CompanyMembership {
  id: number;
  name: string;
  tradeName: string | null;
  ruc: string;
  role: UserRole;
}

export interface MeResponse {
  id: string;
  email: string | null;
  fullName: string;
  role: UserRole;
  tenantId: number;
  active: boolean;
}
