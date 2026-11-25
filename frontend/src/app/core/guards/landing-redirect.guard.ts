import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

export const landingRedirectGuard: CanActivateFn = async () => {
  const auth = inject(AuthService);
  const router = inject(Router);

  try {
    await auth.initialize();
  } catch {
    return router.createUrlTree(['/auth-error']);
  }

  switch (auth.status()) {
    case 'authenticated':
      return router.createUrlTree([auth.defaultRouteForCurrentUser()]);
    case 'company-selection-required':
      return router.createUrlTree(['/select-company']);
    case 'no-company':
      return router.createUrlTree(['/no-company']);
    case 'error':
      return router.createUrlTree(['/auth-error']);
    default:
      return router.createUrlTree(['/login']);
  }
};
