export const dynamic = 'force-dynamic'

import Link from 'next/link'

import {
  getKPIsGlobales,
  getTopEntidadesPorMonto,
  getTopProductos,
  getTopProveedores,
} from '@/lib/queries'
import BarChart from '@/components/BarChart'

function formatMonto(n: number) {
  if (n >= 1_000_000_000) return `Bs. ${(n / 1_000_000_000).toFixed(1)}B`
  if (n >= 1_000_000) return `Bs. ${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `Bs. ${(n / 1_000).toFixed(0)}K`
  return `Bs. ${n.toLocaleString('es-BO')}`
}

function StatCard({
  label,
  value,
  sub,
  color,
}: {
  label: string
  value: string
  sub?: string
  color: string
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className={`w-8 h-1 rounded-full mb-3 ${color}`} />
      <div className="text-2xl font-bold text-gray-900 tabular-nums">{value}</div>
      <div className="text-sm font-medium text-gray-600 mt-1">{label}</div>
      {sub && <div className="text-xs text-gray-400 mt-0.5">{sub}</div>}
    </div>
  )
}

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">{title}</h3>
      {children}
    </div>
  )
}

type CellValue = string | number | null | { text: string; href: string }

function TableCard({
  title,
  headers,
  rows,
  note,
}: {
  title: string
  headers: string[]
  rows: CellValue[][]

  note?: string
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="px-6 py-4 border-b border-gray-100">
        <h3 className="text-sm font-semibold text-gray-700">{title}</h3>
        {note && <p className="text-xs text-gray-400 mt-0.5">{note}</p>}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-50 bg-gray-50">
              {headers.map((h) => (
                <th key={h} className="text-left px-4 py-2.5 font-medium text-gray-500 text-xs">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {rows.map((row, i) => (
              <tr key={i} className="hover:bg-gray-50">
                {row.map((cell, j) => (
                  <td key={j} className={`px-4 py-2.5 text-xs ${j === 0 ? 'text-gray-800 font-medium max-w-xs' : 'text-gray-500 tabular-nums text-right'}`}>
                    {cell !== null && typeof cell === 'object' && 'href' in cell ? (
                      <Link href={cell.href} className="hover:text-blue-600 line-clamp-1">
                        {cell.text}
                      </Link>
                    ) : j === 0 ? (
                      <span className="line-clamp-1">{cell as string | number | null}</span>
                    ) : (
                      (cell as string | number | null) ?? '—'
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default async function DashboardPage() {
  const [kpis, topEntidades, topProductos, topProveedores] = await Promise.all([
    getKPIsGlobales(),
    getTopEntidadesPorMonto(10),
    getTopProductos(15),
    getTopProveedores(10),
  ])

  const entidadData = topEntidades.map((r) => ({
    label: r.entidad.length > 32 ? r.entidad.slice(0, 30) + '…' : r.entidad,
    value: r.monto,
  }))

  const productosRows = topProductos.map((p) => [
    { text: p.descripcion, href: `/producto/${encodeURIComponent(p.descripcion)}` },
    p.clase,
    p.veces,
    formatMonto(p.monto_total),
    `${formatMonto(p.precio_min)} – ${formatMonto(p.precio_max)}`,
  ])

  const proveedoresRows = topProveedores.map((p) => [
    p.proveedor,
    p.contratos,
    formatMonto(p.monto_total),
  ])

  return (
    <main className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
              <span className="text-white text-xs font-bold">S</span>
            </div>
            <div>
              <h1 className="text-lg font-semibold text-gray-900">SICOES Intelligence</h1>
              <p className="text-xs text-gray-500">Contrataciones estatales de Bolivia</p>
            </div>
          </div>
          <nav className="flex items-center gap-4 text-sm">
            <Link href="/" className="text-gray-500 hover:text-gray-800">Procesos</Link>
            <Link href="/items" className="text-gray-500 hover:text-gray-800">Bienes</Link>
            <Link href="/dashboard" className="text-blue-600 font-medium">Dashboard</Link>
          </nav>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 space-y-8">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">Inteligencia de mercado</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            {kpis.totalProcesos.toLocaleString('es-BO')} procesos ·{' '}
            {kpis.totalItems.toLocaleString('es-BO')} ítems indexados · datos de contrataciones estatales de Bolivia
          </p>
        </div>

        {/* KPI Cards */}
        <section>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <StatCard
              label="Procesos indexados"
              value={kpis.totalProcesos.toLocaleString('es-BO')}
              sub="de todas las entidades"
              color="bg-blue-500"
            />
            <StatCard
              label="Monto adjudicado"
              value={formatMonto(kpis.montoTotal)}
              sub="en contratos cerrados"
              color="bg-emerald-500"
            />
            <StatCard
              label="Ítems procesados"
              value={kpis.totalItems.toLocaleString('es-BO')}
              sub="bienes y servicios"
              color="bg-violet-500"
            />
            <StatCard
              label="Proveedores únicos"
              value={kpis.totalProveedores.toLocaleString('es-BO')}
              sub="empresas y personas"
              color="bg-amber-500"
            />
          </div>
        </section>

        {/* Top entidades */}
        <section>
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Por entidad</h2>
          <ChartCard title="Top 10 entidades por monto adjudicado">
            <BarChart
              data={entidadData}
              layout="vertical"
              color="#2563eb"
              format="monto"
            />
          </ChartCard>
        </section>

        {/* Bienes section */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">Bienes más contratados</h2>
            <Link href="/items" className="text-xs text-blue-600 hover:underline">
              Ver buscador de bienes →
            </Link>
          </div>
          {topProductos.length === 0 ? (
            <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
              <p className="text-gray-400 text-sm">No hay ítems procesados aún.</p>
              <p className="text-xs text-gray-400 mt-1">Corré el scraper para poblar esta sección.</p>
            </div>
          ) : (
            <TableCard
              title="Top 15 productos por monto adjudicado total"
              note="Basado en ítems con estado adjudicado"
              headers={['Descripción', 'Categoría UNSPSC', 'Veces', 'Monto total', 'Rango de precio']}
              rows={productosRows}
            />
          )}
        </section>

        {/* Proveedores */}
        <section>
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Proveedores</h2>
          {topProveedores.length === 0 ? (
            <div className="bg-white rounded-xl border border-gray-200 p-8 text-center">
              <p className="text-gray-400 text-sm">No hay proveedores procesados aún.</p>
            </div>
          ) : (
            <TableCard
              title="Top 10 proveedores por monto adjudicado"
              headers={['Proveedor', 'Contratos', 'Monto total']}
              rows={proveedoresRows}
            />
          )}
        </section>
      </div>
    </main>
  )
}
