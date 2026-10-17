export type AuditModule =
  | 'auth'
  | 'ventas'
  | 'facturacion'
  | 'gastos'
  | 'inventario'
  | 'ia'
  | 'configuracion'
  | 'usuarios';

export interface AuditEntry {
  id: string;
  timestamp: string;
  userId: string;
  userName: string;
  module: AuditModule;
  action: string;
  description: string;
}
