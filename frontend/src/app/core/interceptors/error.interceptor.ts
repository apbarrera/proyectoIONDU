import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { ToastService } from '../services/toast.service';
import { SKIP_ERROR_TOAST, apiErrorMessage } from '../utils/api-error.util';
import { isAuthEndpoint, isExpiredTokenError } from './auth.interceptor';

export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const toast = inject(ToastService);

  return next(req).pipe(
    catchError((error: unknown) => {
      // /api/auth/* lo maneja la pantalla de login, y un token vencido lo renueva
      // authInterceptor sin que el usuario lo note: ninguno muestra aviso.
      const handledElsewhere = isAuthEndpoint(req.url) || isExpiredTokenError(error);
      if (!handledElsewhere && !req.context.get(SKIP_ERROR_TOAST)) {
        toast.error(apiErrorMessage(error));
      }
      return throwError(() => error);
    }),
  );
};
