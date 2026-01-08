import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

export const supabase = createClient(
  window.__SUPABASE_URL__,
  window.__SUPABASE_ANON_KEY__
);
