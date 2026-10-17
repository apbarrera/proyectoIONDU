import { TestBed } from '@angular/core/testing';
import { AuthService } from './auth.service';

describe('AuthService', () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    TestBed.configureTestingModule({});
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('al cerrar sesión limpia el localStorage y el sessionStorage', () => {
    localStorage.setItem('iondu-session', '{}');
    localStorage.setItem('iondu-theme', '"dark"');
    sessionStorage.setItem('borrador', '1');

    TestBed.inject(AuthService).logout();

    expect(localStorage.length).toBe(0);
    expect(sessionStorage.length).toBe(0);
  });

  it('al cerrar sesión vacía la caché del service worker', async () => {
    const deleted: string[] = [];
    vi.stubGlobal('caches', {
      keys: async () => ['ngsw:/:db:control', 'ngsw:/:1:assets'],
      delete: async (name: string) => {
        deleted.push(name);
        return true;
      },
    });

    TestBed.inject(AuthService).logout();

    await vi.waitFor(() => expect(deleted).toEqual(['ngsw:/:db:control', 'ngsw:/:1:assets']));
  });

  it('cierra la sesión aunque el navegador bloquee la caché', () => {
    vi.stubGlobal('caches', {
      keys: async () => {
        throw new Error('bloqueado');
      },
    });
    const auth = TestBed.inject(AuthService);

    expect(() => auth.logout()).not.toThrow();
    expect(auth.isAuthenticated()).toBe(false);
  });
});
