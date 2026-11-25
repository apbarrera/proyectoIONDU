import { Routes } from '@angular/router';
import { NewSale } from './pages/new-sale/new-sale';
import { SalesHistory } from './pages/sales-history/sales-history';
import { Customers } from './pages/customers/customers';

export const SALES_ROUTES: Routes = [
  { path: '', redirectTo: 'history', pathMatch: 'full' },
  { path: 'new', component: NewSale },
  { path: 'history', component: SalesHistory },
  { path: 'customers', component: Customers },
];
