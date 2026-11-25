import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { TenantService } from './tenant.service';

describe('TenantService', () => {
  let service: TenantService;
  let httpMock: HttpTestingController;

  const company = {
    id: 7,
    ruc: '1790010937001',
    businessName: 'CAFETERÍA DEMO S.A.',
    tradeName: 'Café Demo',
    economicActivity: null,
    address: null,
    email: 'demo@iondu.ec',
    electronicSignature: { configured: false, expiresAt: null, expiresSoon: false, expired: false },
    billing: null,
  };

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(TenantService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpMock.verify());

  it('carga la empresa y la deja en el signal', () => {
    service.getTenant().subscribe();
    httpMock.expectOne('/api/company').flush(company);
    expect(service.tenant()?.ruc).toBe('1790010937001');
  });

  it('guarda la configuración de facturación completa', () => {
    const billing = {
      environment: 'pruebas' as const,
      establishment: '001',
      emissionPoint: '001',
      requiredToKeepAccounts: false,
      rimpe: true,
      specialTaxpayer: null,
    };
    service.saveBillingSettings(billing).subscribe();

    const req = httpMock.expectOne('/api/company/billing-settings');
    expect(req.request.method).toBe('PUT');
    expect(req.request.body).toEqual(billing);
    req.flush({ ...company, billing });

    expect(service.tenant()?.billing?.rimpe).toBe(true);
  });

  it('sube el .p12 como multipart con los campos archivo y clave', () => {
    const file = new File(['x'], 'firma.p12');
    service.uploadCertificate(file, 'secreta').subscribe();

    const req = httpMock.expectOne('/api/company/certificate');
    expect(req.request.method).toBe('PUT');
    const body = req.request.body as FormData;
    expect(body.get('archivo')).toBeInstanceOf(File);
    expect(body.get('clave')).toBe('secreta');
    req.flush({ mensaje: 'ok', fecha_vencimiento: '2027-03-01' });
  });
});
