import { HttpContextToken, HttpErrorResponse } from '@angular/common/http';

/** Si la petición lleva este contexto en `true`, el interceptor de errores no muestra el aviso. */
export const SKIP_ERROR_TOAST = new HttpContextToken<boolean>(() => false);

const FALLBACK = 'Ocurrió un error inesperado.';

/** Extrae el mensaje del formato de error del backend: `{"error": {"code", "message", "details"}}`. */
export function apiErrorMessage(error: unknown): string {
  if (error instanceof HttpErrorResponse) {
    if (error.status === 0) return 'No se pudo conectar con el servidor. Revisa tu conexión.';
    const message = (error.error as { error?: { message?: unknown } } | null)?.error?.message;
    if (typeof message === 'string' && message) return message;
    return FALLBACK;
  }
  return error instanceof Error ? error.message : FALLBACK;
}

/** Código de error del backend (`INSUFFICIENT_STOCK`, `CUSTOMER_EXISTS`…), si lo hay. */
export function apiErrorCode(error: unknown): string | null {
  if (error instanceof HttpErrorResponse) {
    const code = (error.error as { error?: { code?: unknown } } | null)?.error?.code;
    return typeof code === 'string' ? code : null;
  }
  return null;
}
