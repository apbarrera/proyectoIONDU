import { Routes } from '@angular/router';
import { NewSale } from './pages/new-sale/new-sale';
import { SalesHistory } from './pages/sales-history/sales-history';

export const SALES_ROUTES: Routes = [
  { path: '', redirectTo: 'history', pathMatch: 'full' },
  { path: 'new', component: NewSale },
  { path: 'history', component: SalesHistory },
];
