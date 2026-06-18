export const dynamic = 'force-dynamic'

import Link from 'next/link'
import { notFound } from 'next/navigation'
import {
  getProveedorStats,
  getProveedorContratos,
  getProveedorTopProductos,
} from '@/lib/queries'

type Props = { params: Promise<{ id: string }> }

function formatMonto(n: number | null) {
  if (!n) return '—'
  if (n >= 1_000_000) return `Bs. ${(n / 1_000_000).toFixed(2)}M`
  if (n >= 1_000) return `Bs. ${n.toLocaleString('es-BO', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  return `Bs. ${n}`
}

function formatFecha(f: string | null) {
  if (!f) return '—'
  return new Date(f + 'T00:00:00').toLocaleDateString('es-BO', {
    day: '2-digit', month: 'short', year: 'numeric',
  })
}

function KPI({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="text-2xl font-bold text-gray-900 tabular-nums">{value}</div>
      <div className="text-sm font-medium text-gray-600 mt-1">{label}</div>
      {sub && <div className="text-xs text-gray-400 mt-0.5">{sub}</div>}
    </div>
  )
}

export default async function ProveedorPage({ params }: Props) {
  const { id } = await params
  const numId = parseInt(id, 10)
  if (isNaN(numId)) notFound()

  const [stats, contratos, topProductos] = await Promise.all([
    getProveedorStats(numId),
    getProveedorContratos(numId),
    getProveedorTopProductos(numId),
  ])

  if (!stats) notFound()

  // Agrupar contratos por CUCE (un proceso puede tener varios ítems)
  const porCuce = new Map<string, typeof contratos>()
  for (const c of contratos) {
    if (!porCuce.has(c.cuce)) porCuce.set(c.cuce, [])
    porCuce.get(c.cuce)!.push(c)
  }
  const procesosUnicos = Array.from(porCuce.entries()).sort((a, b) => {
    const fa = a[1][0]?.fecha_publicacion ?? ''
    const fb = b[1][0]?.fecha_publicacion ?? ''
    return fb.localeCompare(fa)
  })

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
            <Link href="/dashboard" className="text-gray-500 hover:text-gray-800">Dashboard</Link>
          </nav>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 space-y-8">

        {/* Breadcrumb + título */}
        <div>
          <nav className="text-xs text-gray-400 mb-2">
            <Link href="/dashboard" className="hover:text-blue-600">Dashboard</Link>
            <span className="mx-2">/</span>
            <span>Proveedor</span>
          </nav>
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-xl bg-blue-100 flex items-center justify-center flex-shrink-0">
              <span className="text-blue-700 font-bold text-lg">
                {stats.nombre.charAt(0).toUpperCase()}
              </span>
            </div>
            <div>
              <h2 className="text-2xl font-bold text-gray-900">{stats.nombre}</h2>
              <p className="text-sm text-gray-500 mt-0.5">Proveedor registrado en SICOES · ID {numId}</p>
            </div>
          </div>
        </div>

        {/* KPIs */}
        <section className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <KPI label="Monto adjudicado" value={formatMonto(stats.monto_total)} sub="suma de contratos ganados" />
          <KPI label="Contratos ganados" value={stats.total_contratos.toLocaleString('es-BO')} sub="ítems adjudicados" />
          <KPI label="Procesos" value={procesosUnicos.length.toLocaleString('es-BO')} sub="procesos de contratación" />
          <KPI label="Entidades compradoras" value={stats.total_entidades.toLocaleString('es-BO')} sub="instituciones del estado" />
        </section>

        {/* Top productos */}
        {topProductos.length > 0 && (
          <section>
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
              Bienes más adjudicados
            </h2>
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-100">
                    <th className="text-left px-4 py-2.5 text-xs font-medium text-gray-500">Producto</th>
                    <th className="text-right px-4 py-2.5 text-xs font-medium text-gray-500">Veces</th>
                    <th className="text-right px-4 py-2.5 text-xs font-medium text-gray-500">Monto total</th>
                    <th className="text-right px-4 py-2.5 text-xs font-medium text-gray-500 hidden md:table-cell">Precio unitario</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {topProductos.map((p, i) => (
                    <tr key={i} className="hover:bg-gray-50 group">
                      <td className="px-4 py-2.5 max-w-xs">
                        <Link
                          href={`/producto/${encodeURIComponent(p.descripcion)}`}
                          className="text-xs font-medium text-gray-800 group-hover:text-blue-600 line-clamp-1 transition-colors"
                        >
                          {p.descripcion}
                        </Link>
                      </td>
                      <td className="px-4 py-2.5 text-right text-xs text-gray-600 tabular-nums">{p.veces}</td>
                      <td className="px-4 py-2.5 text-right text-xs font-semibold text-emerald-700 tabular-nums">
                        {formatMonto(p.monto_total)}
                      </td>
                      <td className="px-4 py-2.5 text-right text-xs text-gray-500 tabular-nums hidden md:table-cell">
                        {p.precio_min === p.precio_max
                          ? formatMonto(p.precio_min)
                          : `${formatMonto(p.precio_min)} – ${formatMonto(p.precio_max)}`}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {/* Historial de procesos */}
        <section>
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
            Historial de contrataciones
            <span className="ml-2 font-normal text-gray-400">{procesosUnicos.length} procesos</span>
          </h2>
          <div className="space-y-3">
            {procesosUnicos.map(([cuce, items]) => {
              const first = items[0]
              const montoTotal = items.reduce((s, i) => s + (i.monto_total ?? 0), 0)
              return (
                <div key={cuce} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                  {/* Cabecera del proceso */}
                  <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3 min-w-0">
                      <span className={`text-xs px-2 py-0.5 rounded font-mono flex-shrink-0 ${
                        first.modalidad === 'CM' ? 'bg-purple-100 text-purple-700' :
                        first.modalidad === 'ANPE' || first.modalidad === 'ANPP' ? 'bg-blue-100 text-blue-700' :
                        'bg-gray-100 text-gray-600'
                      }`}>
                        {first.modalidad ?? '—'}
                      </span>
                      <Link
                        href={`/proceso/${cuce}`}
                        className="text-xs font-mono text-blue-600 hover:underline flex-shrink-0"
                      >
                        {cuce}
                      </Link>
                      <span className="text-xs text-gray-400 flex-shrink-0">{first.entidad_nombre}</span>
                    </div>
                    <div className="flex items-center gap-4 flex-shrink-0 text-right">
                      <span className="text-xs text-gray-400">{formatFecha(first.fecha_publicacion)}</span>
                      <span className="text-xs font-semibold text-emerald-700 tabular-nums">
                        {formatMonto(montoTotal)}
                      </span>
                    </div>
                  </div>
                  {/* Ítems del proceso */}
                  <table className="w-full text-xs">
                    <tbody className="divide-y divide-gray-50">
                      {items.map((item, j) => (
                        <tr key={j} className="hover:bg-gray-50">
                          <td className="px-4 py-2 text-gray-700 max-w-xs">
                            <Link
                              href={`/producto/${encodeURIComponent(item.descripcion_producto)}`}
                              className="hover:text-blue-600 line-clamp-1"
                            >
                              {item.descripcion_producto}
                            </Link>
                          </td>
                          <td className="px-4 py-2 text-gray-400 w-20">
                            {item.cantidad ? `${item.cantidad.toLocaleString('es-BO')} ${item.unidad_medida ?? ''}`.trim() : '—'}
                          </td>
                          <td className="px-4 py-2 text-right text-gray-600 tabular-nums w-28">
                            {formatMonto(item.precio_adjudicado)}
                            <span className="text-gray-400"> /u.</span>
                          </td>
                          <td className="px-4 py-2 text-right font-semibold text-emerald-700 tabular-nums w-28">
                            {formatMonto(item.monto_total)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )
            })}
          </div>
        </section>

      </div>
    </main>
  )
}
