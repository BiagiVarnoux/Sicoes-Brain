export const dynamic = 'force-dynamic'

import Link from 'next/link'

import SiteHeader from '@/components/SiteHeader'
import { ProvisionalBadge } from '@/components/HistUI'
import { getHistData, agruparProductos, num, fmtMonto, fmtNum, type HistItem } from '@/lib/historico'

const valItem = (it: HistItem) => num(it.monto_total) || num(it.precio_adjudicado) * num(it.cantidad)

function norm(s: string) {
  return s.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '')
}

type Props = { searchParams: Promise<{ q?: string }> }

export default async function ProductoIndexPage({ searchParams }: Props) {
  const sp = await searchParams
  const q = (sp.q ?? '').trim()

  const data = await getHistData()
  const grupos = agruparProductos(data.items, data.canonicos)

  let rows = Array.from(grupos.values()).map((g) => {
    const entidades = new Set(g.items.map((i) => i.entidad_codigo).filter(Boolean))
    const precios = g.items
      .map((i) => num(i.precio_adjudicado) || (num(i.cantidad) ? valItem(i) / num(i.cantidad) : 0))
      .filter((p) => p > 0)
    return {
      key: g.key,
      label: g.label,
      provisional: g.provisional,
      unspsc: g.unspsc,
      monto: g.items.reduce((s, it) => s + valItem(it), 0),
      items: g.items.length,
      entidades: entidades.size,
      precioMin: precios.length ? Math.min(...precios) : null,
      precioMax: precios.length ? Math.max(...precios) : null,
    }
  })

  if (q) {
    const nq = norm(q)
    rows = rows.filter((r) => norm(r.label).includes(nq) || (r.unspsc ?? '').includes(q))
  }
  rows.sort((a, b) => b.monto - a.monto)

  return (
    <main className="min-h-screen bg-gray-50">
      <SiteHeader maxWidth="max-w-6xl" />
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 space-y-6">
        <div>
          <Link href="/historico" className="text-xs text-blue-600 hover:underline">← Histórico</Link>
          <h2 className="text-xl font-bold text-gray-900 mt-1">Productos (cross-entidad)</h2>
          <p className="text-xs text-gray-400 mt-0.5">
            Cuánto piden del mismo bien todas las entidades juntas. Clic en un producto para ver qué entidades lo compran y la dispersión de precios.
          </p>
        </div>

        <form className="flex gap-2" action="/historico/producto">
          <input
            name="q"
            defaultValue={q}
            placeholder="Buscar producto o código UNSPSC…"
            className="flex-1 px-3 py-2 text-sm border border-gray-200 rounded-lg bg-white
                       focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button className="px-4 py-2 text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700">Buscar</button>
        </form>

        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50 text-xs text-gray-500">
                <th className="text-left px-4 py-3 font-medium">Producto</th>
                <th className="text-right px-4 py-3 font-medium">Entidades</th>
                <th className="text-right px-4 py-3 font-medium hidden sm:table-cell">Ítems</th>
                <th className="text-right px-4 py-3 font-medium hidden md:table-cell">Precio unit.</th>
                <th className="text-right px-4 py-3 font-medium">Monto</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {rows.length === 0 ? (
                <tr><td colSpan={5} className="px-4 py-10 text-center text-gray-400 text-sm">Sin productos</td></tr>
              ) : (
                rows.map((r) => (
                  <tr key={r.key} className="hover:bg-gray-50 group">
                    <td className="px-4 py-3 max-w-md">
                      <Link href={`/historico/producto/${encodeURIComponent(r.key)}`} className="text-xs font-medium text-gray-800 group-hover:text-blue-600 line-clamp-2 leading-tight inline-flex items-center gap-1.5">
                        {r.label}
                        {r.provisional && <ProvisionalBadge />}
                      </Link>
                      {r.unspsc && <div className="text-[10px] text-gray-400 mt-0.5">UNSPSC {r.unspsc}</div>}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-xs text-gray-700">{r.entidades}</td>
                    <td className="px-4 py-3 text-right tabular-nums text-xs text-gray-600 hidden sm:table-cell">{r.items}</td>
                    <td className="px-4 py-3 text-right tabular-nums text-xs text-gray-500 hidden md:table-cell">
                      {r.precioMin != null
                        ? r.precioMin === r.precioMax
                          ? fmtMonto(r.precioMin)
                          : `${fmtMonto(r.precioMin)} – ${fmtMonto(r.precioMax ?? r.precioMin)}`
                        : '—'}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-xs font-semibold text-emerald-700">{fmtMonto(r.monto)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        <p className="text-xs text-gray-400">{fmtNum(rows.length)} producto{rows.length !== 1 ? 's' : ''}</p>
      </div>
    </main>
  )
}
