import { InjectionToken } from '@angular/core';
import type { Session } from '@supabase/auth-js';

import { supabaseAuth } from './supabase.client';

export interface SupabaseAuthResult<T> {
  data: T;
  error: Error | null;
}

export interface SupabaseAuthGateway {
  getSession(): Promise<
    SupabaseAuthResult<{ session: Session | null }>
  >;

  signInWithPassword(credentials: {
    email: string;
    password: string;
  }): Promise<
    SupabaseAuthResult<{ session: Session | null }>
  >;

  signOut(): Promise<{
    error: Error | null;
  }>;
}

export const SUPABASE_AUTH =
  new InjectionToken<SupabaseAuthGateway>(
    'SUPABASE_AUTH',
    {
      providedIn: 'root',
      factory: () => ({
        getSession: () => supabaseAuth.getSession(),

        signInWithPassword: (credentials) =>
          supabaseAuth.signInWithPassword(credentials),

        signOut: async () => {
          const { error } = await supabaseAuth.signOut({
            scope: 'local',
          });

          return { error };
        },
      }),
    },
  );
