import Link from 'next/link'
import {
  getKPIsGlobales,
  getProcesosporModalidad,
  getProcesosporEstado,
  getTopEntidadesPorMonto,
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

export default async function DashboardPage() {
  const [kpis, porModalidad, porEstado, topEntidades] = await Promise.all([
    getKPIsGlobales(),
    getProcesosporModalidad(),
    getProcesosporEstado(),
    getTopEntidadesPorMonto(10),
  ])

  const modalidadData = porModalidad.map((r) => ({ label: r.modalidad, value: r.total }))
  const estadoData = porEstado.map((r) => ({ label: r.estado, value: r.total }))
  const entidadData = topEntidades.map((r) => ({
    label: r.entidad.length > 32 ? r.entidad.slice(0, 30) + '…' : r.entidad,
    value: r.monto,
  }))

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
            <Link href="/dashboard" className="text-blue-600 font-medium">Dashboard</Link>
          </nav>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 space-y-6">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">Resumen general</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            {kpis.totalProcesos.toLocaleString('es-BO')} procesos indexados · datos de contrataciones estatales de Bolivia
          </p>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <StatCard
            label="Procesos indexados"
            value={kpis.totalProcesos.toLocaleString('es-BO')}
            sub="de todas las entidades"
            color="bg-blue-500"
          />
          <StatCard
            label="Monto adjudicado total"
            value={formatMonto(kpis.montoTotal)}
            sub="suma de contratos"
            color="bg-emerald-500"
          />
          <StatCard
            label="Ítems procesados"
            value={kpis.totalItems.toLocaleString('es-BO')}
            sub="productos y servicios"
            color="bg-violet-500"
          />
          <StatCard
            label="Proveedores únicos"
            value={kpis.totalProveedores.toLocaleString('es-BO')}
            sub="empresas y personas"
            color="bg-amber-500"
          />
        </div>

        {/* Charts row 1 */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <ChartCard title="Procesos por modalidad">
            <BarChart data={modalidadData} color="#2563eb" />
          </ChartCard>
          <ChartCard title="Procesos por estado">
            <BarChart data={estadoData} color="#7c3aed" />
          </ChartCard>
        </div>

        {/* Top entidades */}
        <ChartCard title="Top 10 entidades por monto adjudicado">
          <BarChart
            data={entidadData}
            layout="vertical"
            color="#059669"
            format="monto"
          />
        </ChartCard>
      </div>
    </main>
  )
}
