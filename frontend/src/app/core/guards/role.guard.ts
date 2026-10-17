import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';
import { ToastService } from '../services/toast.service';
import { UserRole } from '../models/user.model';

/**
 * Frontend-only UX gating — real authorization must also be enforced server-side
 * once the API exists. This only hides/blocks navigation for a smoother role-based UX.
 */
export const roleGuard = (allowedRoles: UserRole[]): CanActivateFn => {
  return () => {
    const auth = inject(AuthService);
    const router = inject(Router);
    const toast = inject(ToastService);

    const role = auth.currentUser()?.role;
    if (role && allowedRoles.includes(role)) return true;

    toast.warning('No tienes permisos para acceder a esa sección.');
    return router.createUrlTree([auth.defaultRouteForCurrentUser()]);
  };
};
