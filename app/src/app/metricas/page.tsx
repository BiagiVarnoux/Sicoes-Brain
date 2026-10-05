export const dynamic = 'force-dynamic'

import SiteHeader from '@/components/SiteHeader'
import { supabase } from '@/lib/supabase'

function diasRestantes(fecha: string | null): number | null {
  if (!fecha) return null
  const hoy = new Date(); hoy.setHours(0, 0, 0, 0)
  return Math.round((new Date(fecha + 'T00:00:00').getTime() - hoy.getTime()) / 86_400_000)
}

type RadarRow = {
  relevante: boolean; descartado: boolean; visto: boolean
  modalidad: string | null; fecha_presentacion: string | null
  motivo_descarte: string[] | null
}
type ErpRow = { estado: string | null; ganada: boolean | null }

function Tile({ label, value, sub, color = 'text-gray-900' }: {
  label: string; value: string | number; sub?: string; color?: string
}) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4">
      <div className="text-xs text-gray-500">{label}</div>
      <div className={`text-2xl font-semibold mt-1 ${color}`}>{value}</div>
      {sub && <div className="text-xs text-gray-400 mt-0.5">{sub}</div>}
    </div>
  )
}

function Barra({ label, n, total, color }: { label: string; n: number; total: number; color: string }) {
  const pct = total > 0 ? Math.round((n / total) * 100) : 0
  return (
    <div className="flex items-center gap-3 text-sm">
      <div className="w-28 text-gray-600 shrink-0">{label}</div>
      <div className="flex-1 h-4 rounded bg-gray-100 overflow-hidden">
        <div className={`h-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <div className="w-16 text-right text-gray-500">{n} · {pct}%</div>
    </div>
  )
}

export default async function MetricasPage() {
  const [{ data: radarData }, { data: erpData }] = await Promise.all([
    supabase.from('convocatorias_radar')
      .select('relevante,descartado,visto,modalidad,fecha_presentacion,motivo_descarte'),
    supabase.from('erp_licitaciones').select('estado,ganada'),
  ])
  const radar = (radarData ?? []) as RadarRow[]
  const erp = (erpData ?? []) as ErpRow[]

  const abiertas = radar.filter((r) => {
    const d = diasRestantes(r.fecha_presentacion)
    return r.relevante && !r.descartado && d !== null && d >= 0
  })
  const sinVer = abiertas.filter((r) => !r.visto).length
  const cierran3 = abiertas.filter((r) => (diasRestantes(r.fecha_presentacion) ?? 99) <= 3).length
  const cierran7 = abiertas.filter((r) => (diasRestantes(r.fecha_presentacion) ?? 99) <= 7).length
  const descartadas = radar.filter((r) => r.descartado).length

  const MODS = ['CM', 'ANPE', 'ANPP', 'LP']
  const porMod = MODS.map((m) => ({ m, n: abiertas.filter((r) => (r.modalidad ?? '') === m).length }))

  // descartes por motivo
  const motivos: Record<string, number> = {}
  for (const r of radar) for (const m of (r.motivo_descarte ?? [])) motivos[m] = (motivos[m] ?? 0) + 1
  const motivosOrden = Object.entries(motivos).sort((a, b) => b[1] - a[1])

  // historial ERP
  const totalErp = erp.length
  const ganadas = erp.filter((e) => e.ganada === true).length
  const perdidas = erp.filter((e) => e.estado === 'PERDIDA').length
  const desiertas = erp.filter((e) => e.estado === 'DESIERTA').length
  const tasa = (ganadas + perdidas) > 0 ? Math.round((ganadas / (ganadas + perdidas)) * 100) : 0

  return (
    <div className="min-h-screen bg-gray-50">
      <SiteHeader />
      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8 space-y-8">
        <div>
          <h2 className="text-2xl font-semibold text-gray-900">Métricas</h2>
          <p className="text-sm text-gray-500 mt-1">Resumen del radar y de tu historial de licitaciones.</p>
        </div>

        <section>
          <h3 className="text-sm font-medium text-gray-700 mb-3">Oportunidades abiertas (radar)</h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <Tile label="Relevantes abiertas" value={abiertas.length} color="text-blue-700" />
            <Tile label="Sin ver" value={sinVer} color="text-blue-700" />
            <Tile label="Cierran ≤ 3 días" value={cierran3} color="text-red-600" />
            <Tile label="Cierran ≤ 7 días" value={cierran7} color="text-amber-600" />
          </div>
          <div className="mt-4 rounded-xl border border-gray-200 bg-white p-4 space-y-2">
            <div className="text-xs text-gray-500 mb-1">Por modalidad (abiertas)</div>
            {porMod.map((x) => (
              <Barra key={x.m} label={x.m} n={x.n} total={abiertas.length} color="bg-blue-500" />
            ))}
          </div>
        </section>

        <section>
          <h3 className="text-sm font-medium text-gray-700 mb-3">Tu historial (ERP)</h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <Tile label="Licitaciones" value={totalErp} />
            <Tile label="Ganadas" value={ganadas} sub="adjudicadas/entregadas/cobradas" color="text-emerald-600" />
            <Tile label="Perdidas" value={perdidas} color="text-red-600" />
            <Tile label="Tasa de éxito" value={`${tasa}%`} sub="ganadas / (ganadas+perdidas)"
              color={tasa >= 50 ? 'text-emerald-600' : 'text-amber-600'} />
          </div>
          {desiertas > 0 && (
            <p className="text-xs text-gray-400 mt-2">{desiertas} desierta{desiertas === 1 ? '' : 's'}.</p>
          )}
        </section>

        {motivosOrden.length > 0 && (
          <section>
            <h3 className="text-sm font-medium text-gray-700 mb-3">Por qué descartás (motivos)</h3>
            <div className="rounded-xl border border-gray-200 bg-white p-4 space-y-2">
              {motivosOrden.map(([m, n]) => (
                <Barra key={m} label={m} n={n} total={descartadas || 1} color="bg-rose-400" />
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  )
}
