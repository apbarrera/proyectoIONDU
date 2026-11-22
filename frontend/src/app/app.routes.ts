import { Routes } from '@angular/router';
import { Shell } from './core/layout/shell/shell';
import { authGuard } from './core/guards/auth.guard';
import { guestGuard } from './core/guards/guest.guard';
import { roleGuard } from './core/guards/role.guard';
import { landingRedirectGuard } from './core/guards/landing-redirect.guard';
import { companySelectionGuard } from './core/guards/company-selection.guard';
import { noCompanyGuard } from './core/guards/no-company.guard';
import { authErrorGuard } from './core/guards/auth-error.guard';

export const routes: Routes = [
  {
    path: 'login',
    canActivate: [guestGuard],
    loadChildren: () => import('./features/auth/auth.routes').then((m) => m.AUTH_ROUTES),
  },
  {
    path: 'select-company',
    canActivate: [companySelectionGuard],
    loadComponent: () =>
      import('./features/auth/pages/select-company/select-company').then((m) => m.SelectCompany),
  },
  {
    path: 'no-company',
    canActivate: [noCompanyGuard],
    loadComponent: () =>
      import('./features/auth/pages/no-company/no-company').then((m) => m.NoCompany),
  },
  {
    path: 'auth-error',
    canActivate: [authErrorGuard],
    loadComponent: () =>
      import('./features/auth/pages/auth-error/auth-error').then((m) => m.AuthError),
  },
  {
    path: '',
    component: Shell,
    canActivate: [authGuard],
    children: [
      { path: '', canActivate: [landingRedirectGuard], children: [] },
      {
        path: 'dashboard',
        canActivate: [roleGuard(['admin'])],
        loadChildren: () => import('./features/dashboard/dashboard.routes').then((m) => m.DASHBOARD_ROUTES),
      },
      {
        path: 'sales',
        loadChildren: () => import('./features/sales/sales.routes').then((m) => m.SALES_ROUTES),
      },
      { path: 'billing', redirectTo: 'sales/history', pathMatch: 'prefix' },
      {
        path: 'expenses',
        loadChildren: () => import('./features/expenses/expenses.routes').then((m) => m.EXPENSES_ROUTES),
      },
      {
        path: 'inventory',
        loadChildren: () => import('./features/inventory/inventory.routes').then((m) => m.INVENTORY_ROUTES),
      },
      {
        path: 'ai',
        loadChildren: () => import('./features/ai-agent/ai-agent.routes').then((m) => m.AI_AGENT_ROUTES),
      },
      {
        path: 'recommendations',
        loadChildren: () =>
          import('./features/recommendations/recommendations.routes').then((m) => m.RECOMMENDATIONS_ROUTES),
      },
      {
        path: 'settings',
        loadChildren: () => import('./features/settings/settings.routes').then((m) => m.SETTINGS_ROUTES),
      },
      {
        path: 'audit',
        canActivate: [roleGuard(['admin'])],
        loadChildren: () => import('./features/audit/audit.routes').then((m) => m.AUDIT_ROUTES),
      },
      { path: '**', redirectTo: 'sales' },
    ],
  },
  { path: '**', redirectTo: '' },
];
