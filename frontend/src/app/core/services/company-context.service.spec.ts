import { TestBed } from '@angular/core/testing';
import { CompanyContextService } from './company-context.service';
import { CompanyMembership } from '../models/company.model';

const COMPANY_A: CompanyMembership = {
  id: 1,
  name: 'Empresa A S.A.',
  tradeName: 'Empresa A',
  ruc: '1790000000001',
  role: 'admin',
};

const COMPANY_B: CompanyMembership = {
  id: 2,
  name: 'Empresa B S.A.',
  tradeName: 'Empresa B',
  ruc: '1790000000002',
  role: 'operator',
};

const COMPANY_C: CompanyMembership = {
  id: 3,
  name: 'Empresa C S.A.',
  tradeName: 'Empresa C',
  ruc: '1790000000003',
  role: 'operator',
};

describe('CompanyContextService', () => {
  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({});
  });

  it('restaura la empresa seleccionada si sigue perteneciendo al usuario', () => {
    localStorage.setItem('iondu-company-id', '2');

    const service = TestBed.inject(CompanyContextService);
    service.setCompanies([COMPANY_A, COMPANY_B]);

    expect(service.selectedCompanyId()).toBe(2);
    expect(service.selectedCompany()).toEqual(COMPANY_B);
  });

  it('selecciona automáticamente la única empresa disponible', () => {
    const service = TestBed.inject(CompanyContextService);
    service.setCompanies([COMPANY_A]);

    expect(service.selectedCompanyId()).toBe(1);
    expect(service.selectedCompany()).toEqual(COMPANY_A);
    expect(localStorage.getItem('iondu-company-id')).toBe('1');
  });

  it('rechaza seleccionar una empresa que no pertenece al usuario', () => {
    const service = TestBed.inject(CompanyContextService);
    service.setCompanies([COMPANY_A]);

    expect(service.selectCompany(999)).toBe(false);
    expect(service.selectedCompanyId()).toBe(1);
  });

  it('limpia la selección si la empresa deja de pertenecer al usuario', () => {
    localStorage.setItem('iondu-company-id', '2');

    const service = TestBed.inject(CompanyContextService);
    service.setCompanies([COMPANY_A, COMPANY_B, COMPANY_C]);
    service.setCompanies([COMPANY_A, COMPANY_C]);

    expect(service.selectedCompanyId()).toBeNull();
    expect(service.selectedCompany()).toBeNull();
    expect(localStorage.getItem('iondu-company-id')).toBeNull();
  });
});
