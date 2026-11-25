import { Routes } from '@angular/router';
import { NewExpense } from './pages/new-expense/new-expense';
import { ExpensesHistory } from './pages/expenses-history/expenses-history';
import { EmailDrafts } from './pages/email-drafts/email-drafts';
import { Suppliers } from './pages/suppliers/suppliers';

export const EXPENSES_ROUTES: Routes = [
  { path: '', redirectTo: 'history', pathMatch: 'full' },
  { path: 'new', component: NewExpense },
  { path: 'history', component: ExpensesHistory },
  { path: 'email-drafts', component: EmailDrafts },
  { path: 'suppliers', component: Suppliers },
];
