import { Injectable, computed, inject, signal } from '@angular/core';
import { CompanyMembership } from '../models/company.model';
import { StorageService } from './storage.service';

const STORAGE_KEY = 'iondu-company-id';

@Injectable({ providedIn: 'root' })
export class CompanyContextService {
  private readonly storage = inject(StorageService);

  #companies = signal<CompanyMembership[]>([]);
  #selectedCompanyId = signal<number | null>(
    this.storage.get<number>(STORAGE_KEY),
  );

  readonly companies = this.#companies.asReadonly();
  readonly selectedCompanyId = this.#selectedCompanyId.asReadonly();

  readonly selectedCompany = computed(
    () =>
      this.#companies().find(
        (company) => company.id === this.#selectedCompanyId(),
      ) ?? null,
  );

  setCompanies(companies: CompanyMembership[]): void {
    this.#companies.set(companies);

    const currentId = this.#selectedCompanyId();

    if (currentId !== null && !companies.some((company) => company.id === currentId)) {
      this.clearSelection();
    }

    if (companies.length === 1) {
      this.selectCompany(companies[0].id);
    }
  }

  selectCompany(companyId: number): boolean {
    const company = this.#companies().find((item) => item.id === companyId);

    if (!company) return false;

    this.#selectedCompanyId.set(companyId);
    this.storage.set(STORAGE_KEY, companyId);
    return true;
  }

  clearSelection(): void {
    this.#selectedCompanyId.set(null);
    this.storage.remove(STORAGE_KEY);
  }

  clear(): void {
    this.#companies.set([]);
    this.clearSelection();
  }
}
