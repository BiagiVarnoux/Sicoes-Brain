export const dynamic = 'force-dynamic'

import Link from 'next/link'
import SiteHeader from '@/components/SiteHeader'
import RadarTable from '@/components/RadarTable'
import { supabase } from '@/lib/supabase'
import type { ConvocatoriaRadar, ErpLicitacion, ErpProducto } from '@/lib/types'

type PageProps = {
  searchParams: Promise<{ vista?: string }>
}

const VISTAS = [
  { key: 'relevantes', label: 'Relevantes' },
  { key: 'todas', label: 'Todas' },
  { key: 'descartadas', label: 'Descartadas' },
]

async function getRadar(vista: string): Promise<ConvocatoriaRadar[]> {
  let q = supabase
    .from('convocatorias_radar')
    .select('*')
    .order('fecha_presentacion', { ascending: true })

  if (vista === 'relevantes') {
    q = q.eq('relevante', true).eq('descartado', false)
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
  if (error) {
    console.error('getErpMap', error)
    return {}
  }
  return Object.fromEntries((data ?? []).map((e) => [e.numero_sicoes, e as ErpLicitacion]))
}

async function getErpProductos(): Promise<ErpProducto[]> {
  const { data, error } = await supabase
    .from('erp_productos')
    .select('numero_sicoes,nombre,especificacion,cantidad,precio_entidad,precio_ofertado')
  if (error) {
    console.error('getErpProductos', error)
    return []
  }
  return (data ?? []) as ErpProducto[]
}

export default async function RadarPage({ searchParams }: PageProps) {
  const { vista = 'relevantes' } = await searchParams
  const [rows, erpMap, erpProductos] = await Promise.all([
    getRadar(vista), getErpMap(), getErpProductos(),
  ])

  const relevantes = rows.filter((r) => r.relevante).length
  const nuevas = rows.filter((r) => !r.visto).length

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

        <div className="flex items-center justify-between mb-4">
          <div className="flex gap-1">
            {VISTAS.map((v) => (
              <Link
                key={v.key}
                href={`/radar?vista=${v.key}`}
                className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                  vista === v.key
                    ? 'bg-blue-50 text-blue-700 font-medium'
                    : 'text-gray-500 hover:text-gray-800 hover:bg-gray-100'
                }`}
              >
                {v.label}
              </Link>
            ))}
          </div>
          <div className="text-xs text-gray-500">
            {rows.length} convocatoria{rows.length === 1 ? '' : 's'}
            {vista === 'relevantes' && nuevas > 0 && (
              <span className="ml-2 inline-flex px-2 py-0.5 rounded-full bg-blue-600 text-white font-medium">
                {nuevas} sin ver
              </span>
            )}
          </div>
        </div>

        <RadarTable rows={rows} erpMap={erpMap} erpProductos={erpProductos} />

        {vista === 'relevantes' && (
          <p className="text-xs text-gray-400 mt-4">
            Mostrando {relevantes} relevantes no descartadas, ordenadas por fecha de cierre
            (las más urgentes primero).
          </p>
        )}
      </main>
    </div>
  )
}
