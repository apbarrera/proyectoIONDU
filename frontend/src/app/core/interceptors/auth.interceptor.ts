import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { from, switchMap } from 'rxjs';
import { SUPABASE_SESSION_READER } from '../services/supabase-session.token';
import { CompanyContextService } from '../services/company-context.service';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const isApiRequest = req.url === '/api' || req.url.startsWith('/api/');

  if (!isApiRequest) {
    return next(req);
  }

  const companyContext = inject(CompanyContextService);
  const readSession = inject(SUPABASE_SESSION_READER);

  return from(readSession()).pipe(
    switchMap(({ data }) => {
      let headers = req.headers;

      const accessToken = data.session?.access_token;

      if (accessToken) {
        headers = headers.set('Authorization', `Bearer ${accessToken}`);
      }

      const isCompanyListRequest = req.url === '/api/me/companies';
      const companyId = companyContext.selectedCompanyId();

      if (!isCompanyListRequest && companyId !== null) {
        headers = headers.set('X-Empresa-Id', String(companyId));
      }

      return next(req.clone({ headers }));
    }),
  );
};
