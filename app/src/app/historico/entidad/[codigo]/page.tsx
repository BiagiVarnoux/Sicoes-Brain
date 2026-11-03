export const dynamic = 'force-dynamic'

import Link from 'next/link'

import SiteHeader from '@/components/SiteHeader'
import HistTimeSeriesChart from '@/components/HistTimeSeriesChart'
import HistSeasonalityChart from '@/components/HistSeasonalityChart'
import HistBudgetChart from '@/components/HistBudgetChart'
import { StatCard, SectionTitle, Card, RankList } from '@/components/HistUI'
import {
  getHistData,
  procByCuceMap,
  serieMensual,
  estacionalidad,
  budgetPorAnio,
  proyectarAnual,
  agruparProductos,
  topBy,
  num,
  fmtMonto,
  fmtNum,
} from '@/lib/historico'

const MESES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

const valItem = (it: { monto_total: number | null; precio_adjudicado: number | null; cantidad: number | null }) =>
  num(it.monto_total) || num(it.precio_adjudicado) * num(it.cantidad)

type Props = { params: Promise<{ codigo: string }> }

export default async function EntidadHistoricoPage({ params }: Props) {
  const { codigo: raw } = await params
  const codigo = decodeURIComponent(raw)

  const data = await getHistData()
  const procByCuce = procByCuceMap(data.procesos)

  const items = data.items.filter((it) => it.entidad_codigo === codigo)
  const procesos = data.procesos.filter((p) => p.entidad_codigo === codigo)
  const nombre = data.entidadNombre.get(codigo) ?? codigo

  const montoAdj = items.reduce((s, it) => s + valItem(it), 0)
  const montoEjec = items.reduce((s, it) => s + num(it.monto_ejecutado), 0)
  const grupos = agruparProductos(items, data.canonicos)
  const nProveedores = new Set(items.map((it) => it.proveedor).filter(Boolean)).size

  const serie = serieMensual(items, procByCuce).map((d) => ({
    label: `${MESES[d.mes - 1]} ${String(d.anio).slice(2)}`,
    valor: d.monto,
  }))
  const season = estacionalidad(items, procByCuce, 'entrega')
  const budget = budgetPorAnio(items, procByCuce)

  const proy = proyectarAnual(budget.map((b) => ({ anio: b.anio, valor: b.adjudicado })))
  const serieAnual = proy
    ? [
        ...proy.base.map((p) => ({ label: String(p.anio), valor: p.valor, proyeccion: false })),
        { label: `${proy.nextAnio}*`, valor: proy.nextValor, proyeccion: true },
      ]
    : []

  const topProductos = Array.from(grupos.values())
    .map((g) => ({
      key: g.key,
      label: g.label,
      value: g.items.reduce((s, it) => s + valItem(it), 0),
      provisional: g.provisional,
      sub: `${g.items.length} ítem${g.items.length !== 1 ? 's' : ''}`,
    }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 12)

  const topProveedores = topBy(items, (it) => it.proveedor, valItem, 10).map((r) => ({
    key: r.key,
    label: r.key,
    value: r.value,
    sub: `${fmtNum(r.count)} ítem${r.count !== 1 ? 's' : ''}`,
  }))

  const notFound = procesos.length === 0 && items.length === 0

  return (
    <main className="min-h-screen bg-gray-50">
      <SiteHeader maxWidth="max-w-6xl" />
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 space-y-6">
        <div>
          <Link href="/historico" className="text-xs text-blue-600 hover:underline">← Histórico</Link>
          <h2 className="text-xl font-bold text-gray-900 mt-1">{nombre}</h2>
          <p className="text-xs text-gray-400 mt-0.5">Qué contrata esta entidad en el tiempo · {codigo}</p>
        </div>

        {notFound ? (
          <div className="bg-white rounded-xl border border-gray-200 p-10 text-center text-sm text-gray-400">
            No hay datos históricos para esta entidad.
          </div>
        ) : (
          <>
            <section className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
              <StatCard label="Procesos" value={fmtNum(procesos.length)} color="bg-blue-500" />
              <StatCard label="Ítems" value={fmtNum(items.length)} color="bg-violet-500" />
              <StatCard label="Adjudicado" value={fmtMonto(montoAdj)} color="bg-emerald-500" />
              <StatCard label="Ejecutado" value={fmtMonto(montoEjec)} sub={montoAdj > 0 ? `${Math.round((montoEjec / montoAdj) * 100)}% del adj.` : undefined} color="bg-teal-500" />
              <StatCard label="Proveedores" value={fmtNum(nProveedores)} color="bg-rose-500" />
            </section>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <section>
                <SectionTitle hint="Monto adjudicado por mes">Evolución mensual</SectionTitle>
                <Card>{serie.length > 0 ? <HistTimeSeriesChart data={serie} /> : <Empty />}</Card>
              </section>
              <section>
                <SectionTitle hint="Mes de entrega (FORM500)">Estacionalidad</SectionTitle>
                <Card>{season.some((s) => s.monto > 0) ? <HistSeasonalityChart data={season} campo="entrega" /> : <Empty />}</Card>
              </section>
            </div>

            <section>
              <SectionTitle hint="Presupuestado vs adjudicado vs ejecutado por año">Ejecución presupuestaria</SectionTitle>
              <Card>{budget.length > 0 ? <HistBudgetChart data={budget} /> : <Empty />}</Card>
            </section>

            {proy && (
              <section>
                <SectionTitle hint={`Tendencia lineal · R²=${proy.r2.toFixed(2)}`}>Proyección {proy.nextAnio}</SectionTitle>
                <Card right={<span className="text-xs text-gray-400">estimado: <span className="font-semibold text-blue-600">{fmtMonto(proy.nextValor)}</span></span>}>
                  <HistTimeSeriesChart data={serieAnual} firstProjIndex={serieAnual.length - 1} />
                </Card>
              </section>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <section>
                <SectionTitle hint="Qué compra más · clic para ver cross-entidad">Productos más contratados</SectionTitle>
                <Card>
                  <RankList rows={topProductos} hrefOf={(k) => `/historico/producto/${encodeURIComponent(k)}`} emptyLabel="Sin productos" />
                </Card>
              </section>
              <section>
                <SectionTitle hint="Quién le provee">Proveedores</SectionTitle>
                <Card><RankList rows={topProveedores} emptyLabel="Sin proveedores" /></Card>
              </section>
            </div>
          </>
        )}
      </div>
    </main>
  )
}

function Empty() {
  return <div className="h-[200px] flex items-center justify-center text-sm text-gray-400">Sin datos</div>
}
