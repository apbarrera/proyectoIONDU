export type IdentificationType = 'cedula' | 'ruc' | 'pasaporte' | 'exterior';

/** Cliente de la empresa, tal como lo devuelve `GET /api/customers` (API.md, sección 7). */
export interface Customer {
  id: number;
  identificationType: IdentificationType;
  identification: string;
  name: string;
  address: string | null;
  phone: string | null;
  email: string | null;
  identificationWarning: string | null;
}

export interface CreateCustomerInput {
  identification: string;
  name: string;
  email?: string | null;
}
