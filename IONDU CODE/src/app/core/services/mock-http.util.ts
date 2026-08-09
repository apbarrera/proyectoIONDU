import { Observable, of, throwError } from 'rxjs';
import { delay, mergeMap } from 'rxjs/operators';

export interface SimulateOptions {
  /** ms range for artificial network latency */
  minDelay?: number;
  maxDelay?: number;
  /** force this call to fail, for exercising error states manually */
  forceError?: boolean;
  errorMessage?: string;
}

/**
 * Wraps a mock value the same way HttpClient would return it, so services can be
 * swapped for real HTTP calls later without touching any component.
 */
export function simulateRequest<T>(value: T, opts: SimulateOptions = {}): Observable<T> {
  const { minDelay = 250, maxDelay = 600, forceError = false, errorMessage = 'Error simulado' } = opts;
  const latency = Math.round(minDelay + Math.random() * (maxDelay - minDelay));

  return of(value).pipe(
    delay(latency),
    mergeMap((v) => (forceError ? throwError(() => new Error(errorMessage)) : of(v))),
  );
}
