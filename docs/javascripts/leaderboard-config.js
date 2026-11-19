// Public Supabase config for the savings leaderboard.
//
// This file is loaded *before* leaderboard.js and supplies the service URL and
// anon key it reads from `window.AGI_PROCESOR_SUPABASE_URL` and
// `window.AGI_PROCESOR_SUPABASE_ANON_KEY`. Both are injected at docs-build time
// from the VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY repo secrets (see
// .github/workflows/docs.yml). AGI PROCESOR ships without a leaderboard
// service, so both are empty here and the page renders the graceful
// "Leaderboard not configured yet" message.
//
// The anon key is public by design: Supabase Row-Level Security protects the
// data, so shipping it in the public docs bundle is expected.
window.AGI_PROCESOR_SUPABASE_URL = "";
window.AGI_PROCESOR_SUPABASE_ANON_KEY = "";
