import Link from 'next/link'
import { notFound } from 'next/navigation'
import { getProductoHistorial, getProductoStats } from '@/lib/queries'
import PrecioChart from '@/components/PrecioChart'
import ProveedoresChart from '@/components/ProveedoresChart'

type Props = {
  params: Promise<{ slug: string }>
}

function fmt(n: number | null) {
  if (n == null) return '—'
  return `Bs. ${n.toLocaleString('es-BO', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function fmtMonto(n: number | null) {
  if (n == null || n === 0) return '—'
  if (n >= 1_000_000) return `Bs. ${(n / 1_000_000).toFixed(2)}M`
  if (n >= 1_000) return `Bs. ${n.toLocaleString('es-BO')}`
  return `Bs. ${n}`
}

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="text-2xl font-bold text-gray-900 tabular-nums">{value}</div>
      <div className="text-sm font-medium text-gray-600 mt-1">{label}</div>
      {sub && <div className="text-xs text-gray-400 mt-0.5">{sub}</div>}
    </div>
  )
}

export default async function ProductoPage({ params }: Props) {
  const { slug } = await params
  const descripcion = decodeURIComponent(slug)

  const [historial, stats] = await Promise.all([
    getProductoHistorial(descripcion),
    getProductoStats(descripcion),
  ])

  if (historial.length === 0) notFound()

  const claseNombre = historial.find((h) => h.clase_nombre)?.clase_nombre
  const familiaNombre = historial.find((h) => h.familia_nombre)?.familia_nombre
  const unidad = historial.find((h) => h.unidad_medida)?.unidad_medida

  // Data para gráfico de precio en el tiempo
  const precioData = historial
    .filter((h) => h.precio_adjudicado && h.fecha_publicacion && h.estado_item === 'adjudicado')
    .map((h) => ({
      fecha: h.fecha_publicacion!,
      precio: Number(h.precio_adjudicado),
      proveedor: h.proveedor_nombre ?? 'Sin nombre',
      entidad: h.entidad_nombre ?? '—',
    }))
    .sort((a, b) => a.fecha.localeCompare(b.fecha))

  // Data para gráfico de proveedores (monto por proveedor)
  const proveedoresMap = new Map<string, { monto: number; contratos: number }>()
  historial
    .filter((h) => h.estado_item === 'adjudicado' && h.proveedor_nombre)
    .forEach((h) => {
      const key = h.proveedor_nombre!
      const prev = proveedoresMap.get(key) ?? { monto: 0, contratos: 0 }
      proveedoresMap.set(key, {
        monto: prev.monto + Number(h.monto_total ?? 0),
        contratos: prev.contratos + 1,
      })
    })
  const proveedoresData = Array.from(proveedoresMap.entries())
    .map(([label, v]) => ({ label, value: v.monto, contratos: v.contratos }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 10)

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
        {/* Breadcrumb */}
        <nav className="text-sm text-gray-500">
          <Link href="/items" className="hover:text-blue-600">Bienes</Link>
          <span className="mx-2">/</span>
          <span className="text-gray-700 font-medium line-clamp-1">{descripcion}</span>
        </nav>

        {/* Título del producto */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-xl font-bold text-gray-900 leading-snug">{descripcion}</h2>
          <div className="flex flex-wrap items-center gap-3 mt-3">
            {claseNombre && (
              <span className="text-xs bg-blue-50 text-blue-700 px-2.5 py-1 rounded-full font-medium">
                {claseNombre}
              </span>
            )}
            {familiaNombre && (
              <span className="text-xs bg-gray-100 text-gray-600 px-2.5 py-1 rounded-full">
                {familiaNombre}
              </span>
            )}
            {unidad && (
              <span className="text-xs bg-gray-100 text-gray-500 px-2.5 py-1 rounded-full">
                Unidad: {unidad}
              </span>
            )}
          </div>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <StatCard
            label="Compras registradas"
            value={String(stats?.total_compras ?? historial.length)}
            sub="procesos que incluyen este bien"
          />
          <StatCard
            label="Monto total adjudicado"
            value={fmtMonto(stats?.monto_total ?? null)}
            sub="suma de contratos"
          />
          <StatCard
            label="Precio promedio"
            value={fmt(stats?.precio_promedio ?? null)}
            sub={unidad ? `por ${unidad}` : 'por unidad'}
          />
          <StatCard
            label="Rango de precio"
            value={stats?.precio_min && stats?.precio_max
              ? `${fmt(stats.precio_min)} – ${fmt(stats.precio_max)}`
              : '—'}
            sub="mínimo – máximo adjudicado"
          />
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <StatCard
            label="Proveedores distintos"
            value={String(stats?.total_proveedores ?? 0)}
            sub="que ofertaron este bien"
          />
          <StatCard
            label="Entidades compradoras"
            value={String(stats?.total_entidades ?? 0)}
            sub="organismos del estado"
          />
          <StatCard
            label="Adjudicaciones"
            value={String(stats?.total_adjudicadas ?? 0)}
            sub="de las compras registradas"
          />
          <StatCard
            label="Cantidad total"
            value={stats?.cantidad_total
              ? `${Number(stats.cantidad_total).toLocaleString('es-BO')} ${unidad ?? ''}`
              : '—'}
            sub="unidades adjudicadas"
          />
        </div>

        {/* Gráfico de precio en el tiempo */}
        {precioData.length > 0 && (
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="text-sm font-semibold text-gray-700 mb-1">
              Evolución de precio adjudicado
            </h3>
            <p className="text-xs text-gray-400 mb-4">
              Precio por unidad en cada proceso adjudicado — puntos con distintos colores = distintos proveedores
            </p>
            <PrecioChart data={precioData} />
          </div>
        )}

        {/* Top proveedores */}
        {proveedoresData.length > 0 && (
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h3 className="text-sm font-semibold text-gray-700 mb-1">
              Proveedores que ganaron contratos
            </h3>
            <p className="text-xs text-gray-400 mb-4">Por monto adjudicado total</p>
            <ProveedoresChart data={proveedoresData} />
          </div>
        )}

        {/* Tabla de historial completo */}
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100">
            <h3 className="text-sm font-semibold text-gray-700">Historial completo de compras</h3>
            <p className="text-xs text-gray-400 mt-0.5">{historial.length} registros en la base de datos</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-50 bg-gray-50">
                  <th className="text-left px-4 py-3 font-medium text-gray-500 text-xs">Entidad</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500 text-xs">Proveedor</th>
                  <th className="text-right px-4 py-3 font-medium text-gray-500 text-xs">Precio adj.</th>
                  <th className="text-right px-4 py-3 font-medium text-gray-500 text-xs">Cantidad</th>
                  <th className="text-right px-4 py-3 font-medium text-gray-500 text-xs">Monto total</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500 text-xs">Fecha</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500 text-xs">Estado</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500 text-xs">Proceso</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {historial.map((h) => (
                  <tr key={h.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-xs text-gray-700 max-w-[180px]">
                      <span className="line-clamp-2">{h.entidad_nombre ?? '—'}</span>
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500 max-w-[160px]">
                      {h.proveedor_id ? (
                        <Link href={`/proveedor/${h.proveedor_id}`}
                          className="line-clamp-2 hover:text-blue-600 transition-colors">
                          {h.proveedor_nombre ?? '—'}
                        </Link>
                      ) : (
                        <span className="line-clamp-2">{h.proveedor_nombre ?? '—'}</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs text-right tabular-nums font-medium text-gray-900">
                      {fmt(h.precio_adjudicado)}
                    </td>
                    <td className="px-4 py-3 text-xs text-right tabular-nums text-gray-500">
                      {h.cantidad != null ? `${h.cantidad} ${h.unidad_medida ?? ''}`.trim() : '—'}
                    </td>
                    <td className="px-4 py-3 text-xs text-right tabular-nums font-medium text-gray-800">
                      {fmtMonto(h.monto_total)}
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-400 whitespace-nowrap">
                      {h.fecha_publicacion
                        ? new Date(h.fecha_publicacion).toLocaleDateString('es-BO', {
                            day: '2-digit', month: 'short', year: 'numeric',
                          })
                        : '—'}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-xs px-2 py-0.5 rounded font-medium ${
                        h.estado_item === 'adjudicado'
                          ? 'bg-emerald-100 text-emerald-800'
                          : h.estado_item === 'requerido'
                          ? 'bg-amber-100 text-amber-800'
                          : 'bg-red-100 text-red-700'
                      }`}>
                        {h.estado_item}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs">
                      <Link
                        href={`/proceso/${encodeURIComponent(h.cuce)}`}
                        className="font-mono text-blue-600 hover:text-blue-800 text-xs"
                      >
                        {h.cuce}
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </main>
  )
}
