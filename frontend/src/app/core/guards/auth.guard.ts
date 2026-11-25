import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

export const authGuard: CanActivateFn = async (_route, state) => {
  const auth = inject(AuthService);
  const router = inject(Router);

  try {
    await auth.initialize();
  } catch {
    return router.createUrlTree(['/auth-error']);
  }

  switch (auth.status()) {
    case 'authenticated':
      return true;
    case 'company-selection-required':
      return router.createUrlTree(['/select-company']);
    case 'no-company':
      return router.createUrlTree(['/no-company']);
    case 'error':
      return router.createUrlTree(['/auth-error']);
    default:
      return router.createUrlTree(['/login'], {
        queryParams: { returnUrl: state.url },
      });
  }
};
