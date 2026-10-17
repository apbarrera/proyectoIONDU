import { Routes } from '@angular/router';
import { Products } from './pages/products/products';
import { Recipes } from './pages/recipes/recipes';
import { Production } from './pages/production/production';
import { Movements } from './pages/movements/movements';
import { Adjustments } from './pages/adjustments/adjustments';
import { Alerts } from './pages/alerts/alerts';

export const INVENTORY_ROUTES: Routes = [
  { path: '', redirectTo: 'products', pathMatch: 'full' },
  { path: 'products', component: Products },
  { path: 'recipes', component: Recipes },
  { path: 'production', component: Production },
  { path: 'movements', component: Movements },
  { path: 'adjustments', component: Adjustments },
  { path: 'alerts', component: Alerts },
];
