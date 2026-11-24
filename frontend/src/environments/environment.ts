// Desarrollo (`ng serve`). La ruta es relativa también aquí: proxy.conf.json
// reenvía /api a http://localhost:8000. Nunca usar URLs absolutas al backend.
export const environment = {
  production: false,
  apiUrl: '/api',
  supabaseUrl: 'https://zalpxilruzwbsttkquul.supabase.co',
  supabasePublishableKey: 'sb_publishable_0mDEmxj9Xc7LszqM0R9ESg_-VGGnt03',
};
