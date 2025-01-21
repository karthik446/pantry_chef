import { SupabaseClient } from '@supabase/supabase-js';

export class BaseRepository {
  protected client: SupabaseClient;

  constructor(supabaseClient: SupabaseClient) {
    this.client = supabaseClient;
  }
}
