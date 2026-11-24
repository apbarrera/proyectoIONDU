import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

export const authErrorGuard: CanActivateFn = async () => {
  const auth = inject(AuthService);
  const router = inject(Router);

  try {
    await auth.initialize();
  } catch {
    return true;
  }

  switch (auth.status()) {
    case 'error':
      return true;
    case 'authenticated':
      return router.createUrlTree([auth.defaultRouteForCurrentUser()]);
    case 'company-selection-required':
      return router.createUrlTree(['/select-company']);
    case 'no-company':
      return router.createUrlTree(['/no-company']);
    default:
      return router.createUrlTree(['/login']);
  }
};
