import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { CompanyMembership, MeResponse } from '../models/company.model';

@Injectable({ providedIn: 'root' })
export class MeApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/me`;

  getCompanies(): Observable<CompanyMembership[]> {
    return this.http.get<CompanyMembership[]>(`${this.baseUrl}/companies`);
  }

  getMe(): Observable<MeResponse> {
    return this.http.get<MeResponse>(this.baseUrl);
  }
}
