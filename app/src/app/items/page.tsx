import Link from 'next/link'
import { searchItems, getEntidades } from '@/lib/queries'

function formatMonto(n: number | null) {
  if (!n) return '—'
  if (n >= 1_000_000) return `Bs. ${(n / 1_000_000).toFixed(2)}M`
  if (n >= 1_000) return `Bs. ${n.toLocaleString('es-BO')}`
  return `Bs. ${n}`
}

function formatPrecio(n: number | null) {
  if (!n) return '—'
  return `Bs. ${n.toLocaleString('es-BO', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function EstadoBadge({ estado }: { estado: string }) {
  const map: Record<string, string> = {
    adjudicado: 'bg-emerald-100 text-emerald-800',
    requerido: 'bg-amber-100 text-amber-800',
    desierto: 'bg-red-100 text-red-700',
  }
  const cls = map[estado.toLowerCase()] ?? 'bg-gray-100 text-gray-600'
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${cls}`}>
      {estado}
    </span>
  )
}

type PageProps = {
  searchParams: Promise<{
    q?: string
    entidad?: string
    estado?: string
    page?: string
  }>
}

export default async function ItemsPage({ searchParams }: PageProps) {
  const params = await searchParams
  const [result, entidades] = await Promise.all([
    searchItems({
      q: params.q,
      entidad: params.entidad,
      estado: params.estado,
      page: Number(params.page ?? 1),
    }),
    getEntidades(),
  ])

  const { items, total, page, pages } = result

  const buildUrl = (overrides: Record<string, string | number | undefined>) => {
    const p = new URLSearchParams()
    const merged = { q: params.q, entidad: params.entidad, estado: params.estado, page: params.page, ...overrides }
    Object.entries(merged).forEach(([k, v]) => { if (v) p.set(k, String(v)) })
    return `/items?${p.toString()}`
  }

  return (
    <main className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-5 flex items-center justify-between">
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
            <Link href="/items" className="text-blue-600 font-medium">Buscador de bienes</Link>
            <Link href="/dashboard" className="text-gray-500 hover:text-gray-800">Dashboard</Link>
          </nav>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-6">
        <div>
          <h2 className="text-xl font-semibold text-gray-900">Buscador de bienes y servicios</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            Buscá productos por nombre, filtrá por entidad o estado — {total.toLocaleString('es-BO')} ítems indexados
          </p>
        </div>

        {/* Search form */}
        <form method="GET" action="/items" className="bg-white rounded-xl border border-gray-200 p-4 space-y-3">
          <div className="flex gap-3">
            <input
              name="q"
              defaultValue={params.q}
              placeholder="Ej: bolsa para sangre, reactivo, silla..."
              className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              type="submit"
              className="px-5 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
            >
              Buscar
            </button>
            {(params.q || params.entidad || params.estado) && (
              <Link
                href="/items"
                className="px-4 py-2 text-sm text-gray-500 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                Limpiar
              </Link>
            )}
          </div>
          <div className="flex gap-3 flex-wrap">
            <select
              name="estado"
              defaultValue={params.estado ?? ''}
              className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-700"
            >
              <option value="">Todos los estados</option>
              <option value="adjudicado">Adjudicado</option>
              <option value="requerido">Requerido</option>
              <option value="desierto">Desierto</option>
            </select>
            <select
              name="entidad"
              defaultValue={params.entidad ?? ''}
              className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-700 max-w-xs"
            >
              <option value="">Todas las entidades</option>
              {entidades.map((e) => (
                <option key={e.codigo} value={e.codigo}>{e.nombre}</option>
              ))}
            </select>
          </div>
        </form>

        {/* Results */}
        {items.length === 0 ? (
          <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
            <p className="text-gray-400 text-sm">
              {params.q
                ? `No se encontraron ítems para "${params.q}"`
                : 'Ingresá un término para buscar productos y servicios contratados'}
            </p>
            <p className="text-gray-400 text-xs mt-2">
              Tip: el buscador usa coincidencia de texto — más adelante agregamos búsqueda semántica por IA
            </p>
          </div>
        ) : (
          <>
            <div className="text-xs text-gray-500">
              Mostrando {(page - 1) * 50 + 1}–{Math.min(page * 50, total)} de {total.toLocaleString('es-BO')} resultados
            </div>

            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-100 bg-gray-50">
                      <th className="text-left px-4 py-3 font-medium text-gray-600">Descripción</th>
                      <th className="text-left px-4 py-3 font-medium text-gray-600 hidden md:table-cell">Categoría</th>
                      <th className="text-right px-4 py-3 font-medium text-gray-600">P. adjudicado</th>
                      <th className="text-right px-4 py-3 font-medium text-gray-600 hidden sm:table-cell">Cantidad</th>
                      <th className="text-right px-4 py-3 font-medium text-gray-600">Monto total</th>
                      <th className="text-left px-4 py-3 font-medium text-gray-600 hidden lg:table-cell">Proveedor</th>
                      <th className="text-left px-4 py-3 font-medium text-gray-600 hidden lg:table-cell">Entidad</th>
                      <th className="text-left px-4 py-3 font-medium text-gray-600 hidden xl:table-cell">Fecha</th>
                      <th className="text-left px-4 py-3 font-medium text-gray-600">Estado</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {items.map((item) => (
                      <tr key={item.id} className="hover:bg-gray-50 transition-colors">
                        <td className="px-4 py-3">
                          <Link
                            href={`/proceso/${item.cuce}`}
                            className="font-medium text-gray-900 hover:text-blue-600 line-clamp-2 max-w-xs"
                          >
                            {item.descripcion_producto}
                          </Link>
                          <div className="text-xs text-gray-400 mt-0.5 lg:hidden">
                            {item.entidad_nombre ?? '—'}
                          </div>
                        </td>
                        <td className="px-4 py-3 hidden md:table-cell">
                          {item.clase_nombre ? (
                            <span className="text-xs text-gray-500 line-clamp-1 max-w-[160px]">
                              {item.clase_nombre}
                            </span>
                          ) : (
                            <span className="text-xs text-gray-300">—</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right tabular-nums text-gray-700">
                          {formatPrecio(item.precio_adjudicado)}
                        </td>
                        <td className="px-4 py-3 text-right tabular-nums text-gray-500 hidden sm:table-cell">
                          {item.cantidad != null ? `${item.cantidad} ${item.unidad_medida ?? ''}`.trim() : '—'}
                        </td>
                        <td className="px-4 py-3 text-right tabular-nums font-medium text-gray-900">
                          {formatMonto(item.monto_total)}
                        </td>
                        <td className="px-4 py-3 text-xs text-gray-500 hidden lg:table-cell max-w-[160px]">
                          <span className="line-clamp-2">{item.proveedor_nombre ?? '—'}</span>
                        </td>
                        <td className="px-4 py-3 text-xs text-gray-500 hidden lg:table-cell max-w-[180px]">
                          <span className="line-clamp-2">{item.entidad_nombre ?? '—'}</span>
                        </td>
                        <td className="px-4 py-3 text-xs text-gray-400 hidden xl:table-cell whitespace-nowrap">
                          {item.fecha_publicacion
                            ? new Date(item.fecha_publicacion).toLocaleDateString('es-BO', {
                                day: '2-digit', month: 'short', year: 'numeric',
                              })
                            : '—'}
                        </td>
                        <td className="px-4 py-3">
                          <EstadoBadge estado={item.estado_item} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Pagination */}
            {pages > 1 && (
              <div className="flex items-center justify-center gap-2">
                {page > 1 && (
                  <Link
                    href={buildUrl({ page: page - 1 })}
                    className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
                  >
                    ← Anterior
                  </Link>
                )}
                <span className="text-sm text-gray-500">
                  Página {page} de {pages}
                </span>
                {page < pages && (
                  <Link
                    href={buildUrl({ page: page + 1 })}
                    className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg hover:bg-gray-50"
                  >
                    Siguiente →
                  </Link>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </main>
  )
}
