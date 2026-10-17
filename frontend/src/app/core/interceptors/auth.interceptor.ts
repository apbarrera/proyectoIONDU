import { HttpInterceptorFn } from '@angular/common/http';

/**
 * Pass-through today (no real backend). Once a real API exists this attaches the
 * session token to outgoing requests without any component-level changes.
 */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  return next(req);
};
