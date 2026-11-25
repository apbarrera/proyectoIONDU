export type IdentificationType = 'cedula' | 'ruc' | 'pasaporte' | 'exterior';

/** Cliente de la empresa, tal como lo devuelve GET /api/customers. */
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
  identificationType?: IdentificationType;
  name: string;
  email?: string | null;
  address?: string | null;
  phone?: string | null;
}

/** Campos editables de un cliente; solo se envían los que cambian. */
export type UpdateCustomerInput = Partial<
  Pick<Customer, 'identificationType' | 'identification' | 'name' | 'address' | 'phone' | 'email'>
>;
