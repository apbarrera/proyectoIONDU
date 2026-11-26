import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { UserDirectoryService } from './user-directory.service';
import { CompanyContextService } from './company-context.service';

const ANA = {
  id: 'u-1',
  email: 'ana@empresa.ec',
  fullName: 'Ana Torres',
  role: 'admin' as const,
  active: true,
  createdAt: '2026-11-25T10:00:00-05:00',
};

describe('UserDirectoryService', () => {
  let service: UserDirectoryService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    TestBed.inject(CompanyContextService).setCompanies([
      { id: 7, name: 'Empresa', tradeName: null, ruc: '1790000000001', role: 'admin' },
    ]);
    service = TestBed.inject(UserDirectoryService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('carga los usuarios de la empresa y los adapta al modelo User', () => {
    service.load().subscribe();
    http.expectOne({ method: 'GET', url: '/api/users' }).flush([ANA]);

    const [ana] = service.users();
    expect(ana).toMatchObject({ id: 'u-1', fullName: 'Ana Torres', tenantId: '7' });
    expect(ana.avatarInitials).toBe('AT');
  });

  it('al crear devuelve la contraseña temporal y agrega el usuario a la lista', () => {
    let temporal: string | null = null;
    service
      .createUser({ email: 'ana@empresa.ec', fullName: 'Ana Torres', role: 'admin' })
      .subscribe((created) => (temporal = created.temporaryPassword));

    const request = http.expectOne({ method: 'POST', url: '/api/users' });
    expect(request.request.body).toEqual({
      email: 'ana@empresa.ec',
      fullName: 'Ana Torres',
      role: 'admin',
    });
    request.flush({ user: ANA, temporaryPassword: 'Temporal-1234567' });

    expect(temporal).toBe('Temporal-1234567');
    expect(service.users().map((u) => u.id)).toEqual(['u-1']);
  });

  it('desactivar envía PATCH con active y actualiza la lista', () => {
    service.load().subscribe();
    http.expectOne('/api/users').flush([ANA]);

    service.setActive('u-1', false).subscribe();
    const request = http.expectOne({ method: 'PATCH', url: '/api/users/u-1' });
    expect(request.request.body).toEqual({ active: false });
    request.flush({ ...ANA, active: false });

    expect(service.users()[0].active).toBe(false);
  });

  it('restablecer la contraseña devuelve la temporal nueva', () => {
    let temporal = '';
    service.resetPassword('u-1').subscribe((password) => (temporal = password));

    http
      .expectOne({ method: 'POST', url: '/api/users/u-1/reset-password' })
      .flush({ temporaryPassword: 'Otra-temporal-123' });

    expect(temporal).toBe('Otra-temporal-123');
  });
});
