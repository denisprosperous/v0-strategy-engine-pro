// Server-only Supabase client using the service role key
import { createClient } from "@supabase/supabase-js"

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseServiceKey =
  process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.SUPABASE_SERVICE_KEY || ""

if (!supabaseUrl) {
  throw new Error("NEXT_PUBLIC_SUPABASE_URL is required for server-side Supabase client")
}

if (!supabaseServiceKey) {
  // Intentionally fail fast on server if no service role key is provided
  throw new Error("SUPABASE_SERVICE_ROLE_KEY is required on the server")
}

export const supabaseServer = createClient(supabaseUrl, supabaseServiceKey, {
  auth: { persistSession: false },
})
