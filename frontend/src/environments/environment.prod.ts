// Producción. Nginx (contenedor `web`) reenvía /api al contenedor `api`:
// mismo origen, sin CORS.
export const environment = {
  production: true,
  apiUrl: '/api',
  supabaseUrl: 'https://zalpxilruzwbsttkquul.supabase.co',
  supabasePublishableKey: 'sb_publishable_0mDEmxj9Xc7LszqM0R9ESg_-VGGnt03',
};
