import { InjectionToken } from '@angular/core';
import type { Session } from '@supabase/auth-js';

import { supabaseAuth } from './supabase.client';

export type SupabaseSessionReader = () => Promise<{
  data: { session: Session | null };
}>;

export const SUPABASE_SESSION_READER =
  new InjectionToken<SupabaseSessionReader>(
    'SUPABASE_SESSION_READER',
    {
      providedIn: 'root',
      factory: () => () => supabaseAuth.getSession(),
    },
  );
