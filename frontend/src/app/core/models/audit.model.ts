export type AuditModule =
  | 'auth'
  | 'ventas'
  | 'facturacion'
  | 'gastos'
  | 'inventario'
  | 'ia'
  | 'configuracion'
  | 'usuarios';

/** Registro de GET /api/audit. Lo escribe el backend; el navegador solo lo lee. */
export interface AuditEntry {
  id: string;
  timestamp: string;
  userId: string | null;
  userName: string;
  module: AuditModule;
  action: string;
  description: string;
  entity: string | null;
  entityId: string | null;
}

export interface AuditFilters {
  module?: AuditModule | null;
  from?: string | null;
  to?: string | null;
}
