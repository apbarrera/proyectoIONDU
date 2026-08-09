import { AuditEntry } from '../core/models/audit.model';
import { USER_IDS } from './seed-ids.const';

export const AUDIT_MOCK: AuditEntry[] = [
  {
    id: 'audit-001',
    timestamp: '2026-08-07T13:00:00.000Z',
    userId: USER_IDS.ADMIN,
    userName: 'María Fernanda Salazar',
    module: 'configuracion',
    action: 'Actualizó configuración',
    description: 'Administrador modificó la configuración de la empresa.',
  },
  {
    id: 'audit-002',
    timestamp: '2026-08-07T15:40:00.000Z',
    userId: USER_IDS.OPERATOR,
    userName: 'Juan Carlos Pérez',
    module: 'ventas',
    action: 'Registró venta',
    description: 'Juan registró una venta de Torta de Chocolate x2.',
  },
  {
    id: 'audit-003',
    timestamp: '2026-08-08T09:05:00.000Z',
    userId: USER_IDS.ADMIN,
    userName: 'María Fernanda Salazar',
    module: 'inventario',
    action: 'Ajustó inventario',
    description: 'María ajustó el stock de Chocolate en polvo.',
  },
  {
    id: 'audit-004',
    timestamp: '2026-08-08T11:20:00.000Z',
    userId: USER_IDS.OPERATOR,
    userName: 'Juan Carlos Pérez',
    module: 'ia',
    action: 'Confirmó propuesta de IA',
    description: 'Usuario confirmó una acción propuesta por el Agente IA.',
  },
];
