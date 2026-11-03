export const dynamic = 'force-dynamic'

import Link from 'next/link'
import { Suspense } from 'react'

import SiteHeader from '@/components/SiteHeader'
import HistFilters from '@/components/HistFilters'
import HistTimeSeriesChart from '@/components/HistTimeSeriesChart'
import HistSeasonalityChart from '@/components/HistSeasonalityChart'
import HistBudgetChart from '@/components/HistBudgetChart'
import { StatCard, SectionTitle, Card, RankList, ProvisionalBadge } from '@/components/HistUI'
import {
  getHistData,
  procByCuceMap,
  filtrarItems,
  filtrarProcesos,
  serieMensual,
  estacionalidad,
  budgetPorAnio,
  proyectarAnual,
  agruparProductos,
  topBy,
  num,
  fmtMonto,
  fmtNum,
  type HistFiltros,
} from '@/lib/historico'

const MESES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

type Props = {
  searchParams: Promise<{ entidad?: string; desde?: string; hasta?: string }>
}

export default async function HistoricoPage({ searchParams }: Props) {
  const sp = await searchParams
  const entidadF = sp.entidad ?? ''
  const desdeF = sp.desde ?? ''
  const hastaF = sp.hasta ?? ''

  const data = await getHistData()
  const procByCuce = procByCuceMap(data.procesos)

  const filtros: HistFiltros = {
    entidad: entidadF || undefined,
    anioDesde: desdeF ? Number(desdeF) : null,
    anioHasta: hastaF ? Number(hastaF) : null,
  }

  const items = filtrarItems(data.items, procByCuce, filtros)
  const procesos = filtrarProcesos(data.procesos, filtros)

  // ── KPIs ────────────────────────────────────────────────────────────────
  const montoAdj = items.reduce((s, it) => s + (num(it.monto_total) || num(it.precio_adjudicado) * num(it.cantidad)), 0)
  const montoEjec = items.reduce((s, it) => s + num(it.monto_ejecutado), 0)
  const grupos = agruparProductos(items, data.canonicos)
  const nProductos = grupos.size
  const nProveedores = new Set(items.map((it) => it.proveedor).filter(Boolean)).size
  const hayProvisional = Array.from(grupos.values()).some((g) => g.provisional)

  // ── Series ──────────────────────────────────────────────────────────────
  const serie = serieMensual(items, procByCuce).map((d) => ({
    label: `${MESES[d.mes - 1]} ${String(d.anio).slice(2)}`,
    valor: d.monto,
  }))

  const season = estacionalidad(items, procByCuce, 'entrega')
  const budget = budgetPorAnio(items, procByCuce)

  // ── Proyección anual (monto adjudicado) ───────────────────────────────────
  const anualPts = budget.map((b) => ({ anio: b.anio, valor: b.adjudicado }))
  const proy = proyectarAnual(anualPts)
  const serieAnual = proy
    ? [
        ...proy.base.map((p) => ({ label: String(p.anio), valor: p.valor, proyeccion: false })),
        { label: `${proy.nextAnio}*`, valor: proy.nextValor, proyeccion: true },
      ]
    : []
  const firstProjIndex = proy ? serieAnual.length - 1 : null

  // ── Rankings ──────────────────────────────────────────────────────────────
  const valItem = (it: { monto_total: number | null; precio_adjudicado: number | null; cantidad: number | null }) =>
    num(it.monto_total) || num(it.precio_adjudicado) * num(it.cantidad)

  const topEntidades = topBy(items, (it) => it.entidad_codigo, valItem, 10).map((r) => ({
    key: r.key,
    label: data.entidadNombre.get(r.key) ?? r.key,
    value: r.value,
    sub: `${fmtNum(r.count)} ítem${r.count !== 1 ? 's' : ''}`,
  }))

  const topProveedores = topBy(items, (it) => it.proveedor, valItem, 10).map((r) => ({
    key: r.key,
    label: r.key,
    value: r.value,
    sub: `${fmtNum(r.count)} ítem${r.count !== 1 ? 's' : ''}`,
  }))

  const topProductos = Array.from(grupos.values())
    .map((g) => ({
      key: g.key,
      label: g.label,
      value: g.items.reduce((s, it) => s + valItem(it), 0),
      provisional: g.provisional,
      sub: `${g.items.length} ítem${g.items.length !== 1 ? 's' : ''} · ${new Set(g.items.map((i) => i.entidad_codigo)).size} entidad(es)`,
    }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 10)

  const entidadNombreSel = entidadF ? data.entidadNombre.get(entidadF) : null
  const subtitulo = [entidadNombreSel ?? (entidadF || null), [desdeF, hastaF].filter(Boolean).join('–') || null]
    .filter(Boolean)
    .join(' · ')

  const sinDatos = data.items.length === 0

  return (
    <main className="min-h-screen bg-gray-50">
      <SiteHeader maxWidth="max-w-6xl" />

      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 space-y-6">
        <div>
          <h2 className="text-xl font-bold text-gray-900">
            Análisis histórico
            {subtitulo && <span className="ml-2 text-base font-normal text-blue-600">{subtitulo}</span>}
          </h2>
          <p className="text-xs text-gray-400 mt-0.5">
            Contrataciones adjudicadas en el tiempo — por entidad y por producto.{' '}
            <Link href="/historico/producto" className="text-blue-600 hover:underline">Ver análisis por producto →</Link>
          </p>
        </div>

        <Suspense>
          <HistFilters
            entidades={data.entidades}
            anios={data.anios}
            entidad={entidadF}
            desde={desdeF}
            hasta={hastaF}
          />
        </Suspense>

        {sinDatos ? (
          <div className="bg-white rounded-xl border border-gray-200 p-10 text-center">
            <p className="text-gray-400 text-sm">
              No hay datos históricos todavía. El scraper histórico aún no pobló las tablas <code>hist_*</code>.
            </p>
          </div>
        ) : (
          <>
            {hayProvisional && (
              <div className="flex items-start gap-2 text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded-xl px-4 py-3">
                <ProvisionalBadge />
                <span>
                  Los productos se agrupan por código UNSPSC / descripción como aproximación. La consolidación
                  definitiva (mismo bien escrito distinto por cada entidad) se hará cuando corra la canonicalización por IA.
                </span>
              </div>
            )}

            {/* KPIs */}
            <section className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
              <StatCard label="Procesos" value={fmtNum(procesos.length)} sub={subtitulo || 'histórico'} color="bg-blue-500" />
              <StatCard label="Ítems" value={fmtNum(items.length)} sub="líneas adjudicadas" color="bg-violet-500" />
              <StatCard label="Adjudicado" value={fmtMonto(montoAdj)} sub="monto total" color="bg-emerald-500" />
              <StatCard label="Ejecutado" value={fmtMonto(montoEjec)} sub={montoAdj > 0 ? `${Math.round((montoEjec / montoAdj) * 100)}% del adj.` : '—'} color="bg-teal-500" />
              <StatCard label="Productos" value={fmtNum(nProductos)} sub="bienes distintos" color="bg-amber-500" />
              <StatCard label="Proveedores" value={fmtNum(nProveedores)} sub="adjudicados" color="bg-rose-500" />
            </section>

            {/* Serie temporal + estacionalidad */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <section>
                <SectionTitle hint="Monto adjudicado por mes de publicación">Evolución mensual</SectionTitle>
                <Card>
                  {serie.length > 0 ? <HistTimeSeriesChart data={serie} /> : <Empty />}
                </Card>
              </section>
              <section>
                <SectionTitle hint="Por mes de entrega (FORM500) — en qué época se concentran las entregas">Estacionalidad</SectionTitle>
                <Card>
                  {season.some((s) => s.monto > 0) ? <HistSeasonalityChart data={season} campo="entrega" /> : <Empty />}
                </Card>
              </section>
            </div>

            {/* Presupuestado vs adjudicado vs ejecutado */}
            <section>
              <SectionTitle hint="Cuánto se presupuestó, cuánto se adjudicó y cuánto se ejecutó, por año">
                Presupuestado · adjudicado · ejecutado
              </SectionTitle>
              <Card>{budget.length > 0 ? <HistBudgetChart data={budget} /> : <Empty />}</Card>
            </section>

            {/* Proyección */}
            {proy && (
              <section>
                <SectionTitle hint={`Tendencia lineal del monto adjudicado anual · R²=${proy.r2.toFixed(2)}`}>
                  Proyección {proy.nextAnio}
                </SectionTitle>
                <Card
                  right={
                    <span className="text-xs text-gray-400">
                      estimado {proy.nextAnio}: <span className="font-semibold text-blue-600">{fmtMonto(proy.nextValor)}</span>
                    </span>
                  }
                >
                  <HistTimeSeriesChart data={serieAnual} firstProjIndex={firstProjIndex} />
                  <p className="text-[11px] text-gray-400 mt-2">
                    * Proyección por regresión lineal sobre {proy.base.length} años. Con pocos años de historia es
                    sólo orientativa.
                  </p>
                </Card>
              </section>
            )}

            {/* Rankings: entidades + productos */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <section>
                <SectionTitle hint="Clic para ver el detalle de la entidad">Top entidades por monto</SectionTitle>
                <Card>
                  <RankList rows={topEntidades} hrefOf={(k) => `/historico/entidad/${encodeURIComponent(k)}`} emptyLabel="Sin entidades" />
                </Card>
              </section>
              <section>
                <SectionTitle hint="Cross-entidad · clic para ver qué entidades lo compran">Top productos por monto</SectionTitle>
                <Card>
                  <RankList rows={topProductos} hrefOf={(k) => `/historico/producto/${encodeURIComponent(k)}`} emptyLabel="Sin productos" />
                </Card>
              </section>
            </div>

            {/* Proveedores */}
            <section>
              <SectionTitle hint="Quién gana los contratos (en el alcance filtrado)">Top proveedores por monto</SectionTitle>
              <Card>
                <RankList rows={topProveedores} emptyLabel="Sin proveedores" />
              </Card>
            </section>
          </>
        )}
      </div>
    </main>
  )
}

function Empty() {
  return <div className="h-[200px] flex items-center justify-center text-sm text-gray-400">Sin datos en este rango</div>
}
