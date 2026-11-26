import { Routes } from '@angular/router';
import { Login } from './pages/login/login';
import { ForgotPassword } from './pages/forgot-password/forgot-password';

export const AUTH_ROUTES: Routes = [
  { path: '', component: Login },
  { path: 'forgot', component: ForgotPassword },
];
