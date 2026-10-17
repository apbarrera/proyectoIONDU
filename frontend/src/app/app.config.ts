import {
  ApplicationConfig,
  provideBrowserGlobalErrorListeners,
  provideZonelessChangeDetection,
  isDevMode,
} from '@angular/core';
import { provideRouter, withComponentInputBinding, withViewTransitions } from '@angular/router';
import { provideHttpClient, withInterceptors } from '@angular/common/http';

import { routes } from './app.routes';
import { authInterceptor } from './core/interceptors/auth.interceptor';
import { errorInterceptor } from './core/interceptors/error.interceptor';
import { loadingInterceptor } from './core/interceptors/loading.interceptor';
import { provideServiceWorker } from '@angular/service-worker';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideZonelessChangeDetection(),
    provideRouter(routes, withComponentInputBinding(), withViewTransitions({
      // El nombre de la transición solo existe mientras dura: de forma permanente crearía un
      // contexto de apilamiento que deja los modales por debajo de la cabecera.
      onViewTransitionCreated: ({ transition }) => {
        const root = document.documentElement;
        const done = () => root.classList.remove('is-page-transitioning');
        root.classList.add('is-page-transitioning');
        // Si otra navegación interrumpe esta, la transición se descarta con un error esperado:
        // se maneja aquí para que no aparezca como promesa rechazada sin capturar.
        transition.finished.then(done, done);
      },
    })),
    provideHttpClient(withInterceptors([authInterceptor, loadingInterceptor, errorInterceptor])),
    provideServiceWorker('ngsw-worker.js', {
      enabled: !isDevMode(),
      registrationStrategy: 'registerWhenStable:30000',
    }),
  ],
};
