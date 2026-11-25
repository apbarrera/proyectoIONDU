import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

export const noCompanyGuard: CanActivateFn = async () => {
  const auth = inject(AuthService);
  const router = inject(Router);

  try {
    await auth.initialize();
  } catch {
    return router.createUrlTree(['/auth-error']);
  }

  switch (auth.status()) {
    case 'no-company':
      return true;
    case 'authenticated':
      return router.createUrlTree([auth.defaultRouteForCurrentUser()]);
    case 'company-selection-required':
      return router.createUrlTree(['/select-company']);
    case 'error':
      return router.createUrlTree(['/auth-error']);
    default:
      return router.createUrlTree(['/login']);
  }
};
