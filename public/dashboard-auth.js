import { getSupabase } from "/supabase-client.js";
const supabase = getSupabase();

const { data } = await supabase.auth.getSession();
if (!data.session) {
  window.location.href = "/login";
}
window.__SUPABASE_ACCESS_TOKEN__ = data.session.access_token;

// optional: expose user email/name
window.__SUPABASE_USER__ = data.session.user;
