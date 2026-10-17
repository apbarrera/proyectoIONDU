import { Routes } from '@angular/router';
import { NewInvoice } from './pages/new-invoice/new-invoice';
import { BillingHistory } from './pages/billing-history/billing-history';

export const BILLING_ROUTES: Routes = [
  { path: '', redirectTo: 'history', pathMatch: 'full' },
  { path: 'new', component: NewInvoice },
  { path: 'history', component: BillingHistory },
];
