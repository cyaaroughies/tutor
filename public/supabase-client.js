import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

export function getSupabase() {
  const url = window.__SUPABASE_URL__;
  const anon = window.__SUPABASE_ANON_KEY__;
  if (!url || !anon) throw new Error("Missing Supabase URL/ANON key on window");
  return createClient(url, anon);
}
