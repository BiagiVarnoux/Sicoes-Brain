import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

// cache: 'no-store' en cada fetch para que Next.js Data Cache nunca sirva
// resultados viejos de Supabase — sin esto las páginas dinámicas pueden mostrar
// datos del momento del build aunque la DB haya cambiado.
export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  global: {
    fetch: (url: RequestInfo | URL, options: RequestInit = {}) =>
      fetch(url, { ...options, cache: 'no-store' }),
  },
})
