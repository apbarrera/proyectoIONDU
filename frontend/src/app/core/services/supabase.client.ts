import { GoTrueClient } from '@supabase/auth-js';
import { environment } from '../../../environments/environment';

const supabaseUrl = environment.supabaseUrl.replace(/\/+$/, '');
const projectRef = new URL(supabaseUrl).hostname.split('.')[0];

export const supabaseAuth = new GoTrueClient({
  url: `${supabaseUrl}/auth/v1`,
  headers: {
    apikey: environment.supabasePublishableKey,
    Authorization: `Bearer ${environment.supabasePublishableKey}`,
  },
  storageKey: `sb-${projectRef}-auth-token`,
  autoRefreshToken: true,
  persistSession: true,
  detectSessionInUrl: true,
  flowType: 'pkce',
});
