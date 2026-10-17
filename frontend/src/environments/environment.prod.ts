// Producción. Nginx (contenedor `web`) reenvía /api al contenedor `api`:
// mismo origen, sin CORS.
export const environment = {
  production: true,
  apiUrl: '/api',
};
