import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { ToastService } from '../services/toast.service';
import { SKIP_ERROR_TOAST, apiErrorMessage } from '../utils/api-error.util';

export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const toast = inject(ToastService);

  return next(req).pipe(
    catchError((error: unknown) => {
      if (!req.context.get(SKIP_ERROR_TOAST)) {
        toast.error(apiErrorMessage(error));
      }
      return throwError(() => error);
    }),
  );
};
