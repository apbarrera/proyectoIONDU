import { UserRole } from '../../models/user.model';

export interface NavChild {
  label: string;
  link: string;
  roles?: UserRole[];
}

export interface NavItem {
  label: string;
  icon: string;
  link: string;
  roles: UserRole[];
  children?: NavChild[];
}

const BOTH: UserRole[] = ['admin', 'operator'];

export const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', icon: '📊', link: '/dashboard', roles: ['admin'] },
  {
    label: 'Ventas',
    icon: '🛒',
    link: '/sales',
    roles: BOTH,
    children: [
      { label: 'Nueva venta', link: '/sales/new' },
      { label: 'Historial de ventas', link: '/sales/history' },
    ],
  },
  {
    label: 'Facturación',
    icon: '🧾',
    link: '/billing',
    roles: BOTH,
    children: [
      { label: 'Nueva factura', link: '/billing/new' },
      { label: 'Facturas emitidas', link: '/billing/history' },
    ],
  },
  {
    label: 'Gastos',
    icon: '💸',
    link: '/expenses',
    roles: BOTH,
    children: [
      { label: 'Registrar gasto', link: '/expenses/new' },
      { label: 'Historial', link: '/expenses/history' },
      { label: 'Facturas recibidas', link: '/expenses/email-drafts' },
    ],
  },
  {
    label: 'Inventario',
    icon: '📦',
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
  { label: 'Agente IA', icon: '🤖', link: '/ai', roles: BOTH },
  { label: 'Recomendaciones', icon: '💡', link: '/recommendations', roles: BOTH },
  {
    label: 'Configuración',
    icon: '⚙️',
    link: '/settings/company',
    roles: BOTH,
    children: [
      { label: 'Empresa', link: '/settings/company' },
      { label: 'Usuarios', link: '/settings/users', roles: ['admin'] },
      { label: 'Configuración IA', link: '/settings/ai' },
      { label: 'Preferencias', link: '/settings/preferences' },
    ],
  },
  { label: 'Auditoría', icon: '🕘', link: '/audit', roles: ['admin'] },
];
