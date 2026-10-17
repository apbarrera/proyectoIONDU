import { IconName } from '../../../shared/icons/icons.generated';
import { UserRole } from '../../models/user.model';

export interface NavChild {
  label: string;
  link: string;
  roles?: UserRole[];
}

export interface NavItem {
  label: string;
  icon: IconName;
  link: string;
  roles: UserRole[];
  children?: NavChild[];
}

const BOTH: UserRole[] = ['admin', 'operator'];

export const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', icon: 'dashboard', link: '/dashboard', roles: ['admin'] },
  {
    label: 'Ventas',
    icon: 'sales',
    link: '/sales',
    roles: BOTH,
    children: [
      { label: 'Historial de ventas', link: '/sales/history' },
      { label: 'Nueva venta', link: '/sales/new' },
    ],
  },
  {
    label: 'Gastos',
    icon: 'expenses',
    link: '/expenses',
    roles: BOTH,
    children: [
      { label: 'Historial', link: '/expenses/history' },
      { label: 'Registrar gasto', link: '/expenses/new' },
      { label: 'Facturas recibidas', link: '/expenses/email-drafts' },
    ],
  },
  {
    label: 'Inventario',
    icon: 'inventory',
    link: '/inventory/products',
    roles: BOTH,
    children: [
      { label: 'Productos', link: '/inventory/products' },
      { label: 'Recetas', link: '/inventory/recipes' },
      { label: 'Fabricación', link: '/inventory/production' },
      { label: 'Movimientos', link: '/inventory/movements' },
      { label: 'Ajustes', link: '/inventory/adjustments' },
      { label: 'Alertas de stock', link: '/inventory/alerts' },
    ],
  },
  { label: 'Agente IA', icon: 'ai', link: '/ai', roles: BOTH },
  { label: 'Recomendaciones', icon: 'recommendations', link: '/recommendations', roles: BOTH },
  {
    label: 'Configuración',
    icon: 'settings',
    link: '/settings/company',
    roles: BOTH,
    children: [
      { label: 'Empresa', link: '/settings/company' },
      { label: 'Usuarios', link: '/settings/users', roles: ['admin'] },
      { label: 'Configuración IA', link: '/settings/ai' },
      { label: 'Preferencias', link: '/settings/preferences' },
    ],
  },
  { label: 'Auditoría', icon: 'audit', link: '/audit', roles: ['admin'] },
];
