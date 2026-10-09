export const dynamic = 'force-dynamic'

import Link from 'next/link'
import SiteHeader from '@/components/SiteHeader'
import RadarTable from '@/components/RadarTable'
import { supabase } from '@/lib/supabase'
import type {
  ConvocatoriaRadar, ErpLicitacion, ErpProducto, ConvocatoriaSpecs,
} from '@/lib/types'

type Params = { vista?: string; mod?: string; urg?: string; sinver?: string; pub?: string; agr?: string }
type PageProps = { searchParams: Promise<Params> }

// Buckets de recencia por fecha de publicación (días desde que se publicó).
const PUBS = [
  { key: '1', label: '📅 Hoy' },
  { key: '3', label: 'Últimos 3 días' },
  { key: '7', label: 'Última semana' },
]

const VISTAS = [
  { key: 'relevantes', label: 'Relevantes' },
  { key: 'interesan', label: '★ Interesan' },
  { key: 'todas', label: 'Todas' },
  { key: 'descartadas', label: 'Descartadas' },
]
const MODALIDADES = ['CM', 'ANPE', 'ANPP', 'LP']

function dias(fecha: string | null): number | null {
  if (!fecha) return null
  const hoy = new Date(); hoy.setHours(0, 0, 0, 0)
  return Math.round((new Date(fecha + 'T00:00:00').getTime() - hoy.getTime()) / 86_400_000)
}

// Días transcurridos desde la publicación (0 = hoy, positivo = pasado).
function diasDesde(fecha: string | null): number | null {
  if (!fecha) return null
  const hoy = new Date(); hoy.setHours(0, 0, 0, 0)
  return Math.round((hoy.getTime() - new Date(fecha + 'T00:00:00').getTime()) / 86_400_000)
}

async function getRadar(vista: string): Promise<ConvocatoriaRadar[]> {
  let q = supabase
    .from('convocatorias_radar')
    .select('*')
    .order('fecha_publicacion', { ascending: false, nullsFirst: false })
    .order('fecha_presentacion', { ascending: true })

  if (vista === 'relevantes') {
    q = q.eq('relevante', true).eq('descartado', false)
  } else if (vista === 'interesan') {
    q = q.eq('interesa', true).eq('descartado', false)
  } else if (vista === 'descartadas') {
    q = q.eq('descartado', true)
  } else {
    q = q.eq('descartado', false)
  }

  const { data, error } = await q
  if (error) {
    console.error('getRadar', error)
    return []
  }
  return (data ?? []) as ConvocatoriaRadar[]
}

async function getErpMap(): Promise<Record<string, ErpLicitacion>> {
  const { data, error } = await supabase
    .from('erp_licitaciones')
    .select('numero_sicoes,nombre,entidad,tipo_proceso,estado,ganada,fecha_presentacion')
  if (error) { console.error('getErpMap', error); return {} }
  return Object.fromEntries((data ?? []).map((e) => [e.numero_sicoes, e as ErpLicitacion]))
}

async function getErpProductos(): Promise<ErpProducto[]> {
  const { data, error } = await supabase
    .from('erp_productos')
    .select('numero_sicoes,nombre,especificacion,cantidad,precio_entidad,precio_ofertado')
  if (error) { console.error('getErpProductos', error); return [] }
  return (data ?? []) as ErpProducto[]
}

async function getSpecsMap(): Promise<Record<string, ConvocatoriaSpecs>> {
  const { data, error } = await supabase.from('convocatoria_specs').select('cuce,items')
  if (error) { console.error('getSpecsMap', error); return {} }
  return Object.fromEntries((data ?? []).map((e) => [e.cuce, e as ConvocatoriaSpecs]))
}

export default async function RadarPage({ searchParams }: PageProps) {
  const sp = await searchParams
  const vista = sp.vista ?? 'relevantes'
  const { mod, urg, sinver, pub, agr } = sp
  const agrupar = agr === '1'
  const [rowsRaw, erpMap, erpProductos, specsMap] = await Promise.all([
    getRadar(vista), getErpMap(), getErpProductos(), getSpecsMap(),
  ])

  // Filtros combinables (sobre la vista)
  let rows = rowsRaw
  if (mod) rows = rows.filter((r) => (r.modalidad ?? '') === mod)
  if (urg) rows = rows.filter((r) => { const d = dias(r.fecha_presentacion); return d !== null && d >= 0 && d <= 7 })
  if (sinver) rows = rows.filter((r) => !r.visto)
  if (pub) rows = rows.filter((r) => { const d = diasDesde(r.fecha_publicacion); return d !== null && d >= 0 && d <= Number(pub) })

  const nuevas = rows.filter((r) => !r.visto).length

  const buildUrl = (ov: Partial<Params>) => {
    const p = new URLSearchParams()
    const m: Params = { vista, mod, urg, sinver, pub, agr, ...ov }
    Object.entries(m).forEach(([k, v]) => { if (v) p.set(k, String(v)) })
    return `/radar?${p.toString()}`
  }
  const chip = (active: boolean) =>
    `px-2.5 py-1 rounded-full text-xs border transition-colors ${
      active ? 'bg-blue-600 text-white border-blue-600'
             : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'}`

  return (
    <div className="min-h-screen bg-gray-50">
      <SiteHeader />
      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
        <div className="mb-6">
          <h2 className="text-2xl font-semibold text-gray-900">Radar de convocatorias</h2>
          <p className="text-sm text-gray-500 mt-1">
            Oportunidades abiertas de tus rubros (computación + etiquetas). Filtradas por
            diccionario 📖 y por IA 🤖.
          </p>
        </div>

        {/* Pestañas */}
        <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
          <div className="flex gap-1">
            {VISTAS.map((v) => (
              <Link key={v.key} href={buildUrl({ vista: v.key })}
                className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                  vista === v.key ? 'bg-blue-50 text-blue-700 font-medium'
                                  : 'text-gray-500 hover:text-gray-800 hover:bg-gray-100'}`}>
                {v.label}
              </Link>
            ))}
          </div>
          <div className="text-xs text-gray-500">
            {rows.length} convocatoria{rows.length === 1 ? '' : 's'}
            {nuevas > 0 && (
              <span className="ml-2 inline-flex px-2 py-0.5 rounded-full bg-blue-600 text-white font-medium">
                {nuevas} sin ver
              </span>
            )}
          </div>
        </div>

        {/* Filtros */}
        <div className="flex items-center gap-2 mb-4 flex-wrap">
          <span className="text-xs text-gray-400">Filtros:</span>
          <Link href={buildUrl({ urg: urg ? '' : '7' })} className={chip(!!urg)}>⏰ Cierran ≤ 7 días</Link>
          <Link href={buildUrl({ sinver: sinver ? '' : '1' })} className={chip(!!sinver)}>👁 Sin ver</Link>
          <span className="mx-1 text-gray-300">·</span>
          <span className="text-xs text-gray-400">Publicación:</span>
          {PUBS.map((pb) => (
            <Link key={pb.key} href={buildUrl({ pub: pub === pb.key ? '' : pb.key })} className={chip(pub === pb.key)}>{pb.label}</Link>
          ))}
          <span className="mx-1 text-gray-300">·</span>
          {MODALIDADES.map((m) => (
            <Link key={m} href={buildUrl({ mod: mod === m ? '' : m })} className={chip(mod === m)}>{m}</Link>
          ))}
          <span className="mx-1 text-gray-300">·</span>
          <Link href={buildUrl({ agr: agrupar ? '' : '1' })} className={chip(agrupar)}>🗓 Agrupar por publicación</Link>
          {(mod || urg || sinver || pub || agrupar) && (
            <Link href={buildUrl({ mod: '', urg: '', sinver: '', pub: '', agr: '' })} className="text-xs text-gray-400 hover:text-gray-700 underline ml-1">
              limpiar
            </Link>
          )}
        </div>

        <RadarTable rows={rows} erpMap={erpMap} erpProductos={erpProductos} specsMap={specsMap} agrupar={agrupar} />

        {vista === 'interesan' && rows.length === 0 && (
          <p className="text-xs text-gray-400 mt-4">
            Todavía no marcaste ninguna con ★. Usá el botón “☆ Me interesa” en las convocatorias.
          </p>
        )}
      </main>
    </div>
  )
}
