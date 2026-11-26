import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';

import { Users } from './users';

describe('Users', () => {
  let component: Users;
  let fixture: ComponentFixture<Users>;
  let http: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Users],
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    }).compileComponents();

    fixture = TestBed.createComponent(Users);
    component = fixture.componentInstance;
    http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
  });

  it('carga los usuarios desde la API al abrir', () => {
    http.expectOne('/api/users').flush([
      {
        id: 'u-1',
        email: 'ana@empresa.ec',
        fullName: 'Ana Torres',
        role: 'admin',
        active: true,
        createdAt: '2026-11-25T10:00:00-05:00',
      },
    ]);
    expect(component.userDirectory.users().length).toBe(1);
  });

  it('muestra la contraseña temporal una sola vez tras crear un usuario', () => {
    http.expectOne('/api/users').flush([]);
    component.openCreate();
    component.form.setValue({ fullName: 'Luis Pérez', email: 'luis@empresa.ec', role: 'operator' });

    component.save();
    http.expectOne({ method: 'POST', url: '/api/users' }).flush({
      user: {
        id: 'u-2',
        email: 'luis@empresa.ec',
        fullName: 'Luis Pérez',
        role: 'operator',
        active: true,
        createdAt: '2026-11-25T10:00:00-05:00',
      },
      temporaryPassword: 'Temporal-1234567',
    });

    expect(component.formOpen()).toBe(false);
    expect(component.credentials()?.password).toBe('Temporal-1234567');
    component.closeCredentials();
    expect(component.credentials()).toBeNull();
  });
});
