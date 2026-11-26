import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { vi } from 'vitest';

import { ResetPassword } from './reset-password';

const TOKEN = 'abcdefghijklmnopqrstuvwxyz0123456789';

describe('ResetPassword', () => {
  let fixture: ComponentFixture<ResetPassword>;
  let http: HttpTestingController;

  async function crear(token: string) {
    await TestBed.configureTestingModule({
      imports: [ResetPassword],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: ActivatedRoute, useValue: { queryParamMap: of(convertToParamMap({ token })) } },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(ResetPassword);
    http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
  }

  afterEach(() => http.verify());

  it('sin token muestra que el enlace no es válido', async () => {
    await crear('');
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('El enlace no es válido');
  });

  it('exige el mínimo y que ambas contraseñas coincidan', async () => {
    await crear(TOKEN);
    const component = fixture.componentInstance;
    component.form.setValue({ password: 'corta', confirm: 'corta' });
    expect(component.form.invalid).toBe(true);
    component.form.setValue({ password: 'Clave-segura-2026', confirm: 'Otra-clave-2026' });
    expect(component.form.errors?.['mismatch']).toBe(true);
    component.submit();
    http.expectNone('/api/auth/password-reset/confirm');
  });

  it('envía el token con la nueva contraseña y vuelve al login', async () => {
    await crear(TOKEN);
    const navigate = vi.spyOn(TestBed.inject(Router), 'navigateByUrl').mockResolvedValue(true);
    const component = fixture.componentInstance;
    component.form.setValue({ password: 'Clave-segura-2026', confirm: 'Clave-segura-2026' });

    component.submit();

    const request = http.expectOne({ method: 'POST', url: '/api/auth/password-reset/confirm' });
    expect(request.request.body).toEqual({ token: TOKEN, newPassword: 'Clave-segura-2026' });
    request.flush(null, { status: 204, statusText: 'No Content' });
    expect(navigate).toHaveBeenCalledWith('/login');
  });
});
