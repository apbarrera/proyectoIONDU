export type BillingEnvironment = 'pruebas' | 'produccion';

export interface BillingSettings {
  environment: BillingEnvironment;
  /** 3 dígitos. */
  establishment: string;
  /** 3 dígitos. */
  emissionPoint: string;
  requiredToKeepAccounts: boolean;
  rimpe: boolean;
  /** Número de resolución de contribuyente especial, o `null`. */
  specialTaxpayer: string | null;
}

export interface ElectronicSignature {
  configured: boolean;
  /** Fecha `AAAA-MM-DD`; `null` si no hay firma. */
  expiresAt: string | null;
  /** Faltan 30 días o menos (alerta RNF-25). */
  expiresSoon: boolean;
  expired: boolean;
  /** Modo demostración: las facturas se autorizan sin .p12 ni SRI y no tienen validez tributaria. */
  simulated?: boolean;
}

/** Empresa activa, tal como la devuelve `GET /api/company` (API.md, sección 10). */
export interface Tenant {
  id: number;
  businessName: string;
  tradeName: string | null;
  ruc: string;
  economicActivity: string | null;
  address: string | null;
  email: string;
  electronicSignature: ElectronicSignature;
  /** `null` mientras la empresa no configure su facturación: sin ella no se puede emitir. */
  billing: BillingSettings | null;
}

/** Campos de la empresa que se pueden editar (el RUC no). */
export type TenantChanges = Partial<
  Pick<Tenant, 'businessName' | 'tradeName' | 'economicActivity' | 'address' | 'email'>
>;
