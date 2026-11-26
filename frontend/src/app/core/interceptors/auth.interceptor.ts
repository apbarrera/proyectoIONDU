import { HttpErrorResponse, HttpInterceptorFn, HttpRequest } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, from, switchMap, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';
import { AuthTokenService } from '../services/auth-token.service';
import { CompanyContextService } from '../services/company-context.service';

function isApiRequest(url: string): boolean {
  return url === '/api' || url.startsWith('/api/');
}

/** /api/auth/* usa la cookie de renovación, no el token de acceso. */
export function isAuthEndpoint(url: string): boolean {
  return url.startsWith('/api/auth/');
}

export function isExpiredTokenError(error: unknown): boolean {
  return (
    error instanceof HttpErrorResponse &&
    error.status === 401 &&
    error.error?.error?.code === 'TOKEN_EXPIRED'
  );
}

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  if (!isApiRequest(req.url) || isAuthEndpoint(req.url)) {
    return next(req);
  }

  const tokens = inject(AuthTokenService);
  const companyContext = inject(CompanyContextService);
  const auth = inject(AuthService);
  const router = inject(Router);

  const send = (token: string | null) => next(withHeaders(req, token, companyContext));

  const endSession = (error: unknown) => {
    auth.handleSessionExpired();
    void router.navigateByUrl('/login');
    return throwError(() => error);
  };

  // Token por vencer: se renueva antes de enviar.
  const request$ = tokens.isExpiringSoon()
    ? from(tokens.refresh()).pipe(
        switchMap((session) =>
          session
            ? send(session.accessToken)
            : endSession(new HttpErrorResponse({ status: 401, url: req.url })),
        ),
      )
    : send(tokens.accessToken);

  return request$.pipe(
    catchError((error: unknown) => {
      if (!isExpiredTokenError(error)) return throwError(() => error);

      // El servidor dice que el token venció: se renueva una vez y se repite la petición.
      return from(tokens.refresh()).pipe(
        switchMap((session) => (session ? send(session.accessToken) : endSession(error))),
      );
    }),
  );
};

function withHeaders(
  req: HttpRequest<unknown>,
  token: string | null,
  companyContext: CompanyContextService,
): HttpRequest<unknown> {
  let headers = req.headers;

  if (token) {
    headers = headers.set('Authorization', `Bearer ${token}`);
  }

  const isCompanyListRequest = req.url === '/api/me/companies';
  const companyId = companyContext.selectedCompanyId();

  if (!isCompanyListRequest && companyId !== null) {
    headers = headers.set('X-Empresa-Id', String(companyId));
  }

  return req.clone({ headers });
}
