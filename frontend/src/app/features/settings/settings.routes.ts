import { Routes } from '@angular/router';
import { Company } from './pages/company/company';
import { Users } from './pages/users/users';
import { Ai } from './pages/ai/ai';
import { Preferences } from './pages/preferences/preferences';
import { roleGuard } from '../../core/guards/role.guard';

export const SETTINGS_ROUTES: Routes = [
  { path: '', redirectTo: 'company', pathMatch: 'full' },
  { path: 'company', component: Company },
  { path: 'users', component: Users, canActivate: [roleGuard(['admin'])] },
  { path: 'ai', component: Ai },
  { path: 'preferences', component: Preferences },
];
