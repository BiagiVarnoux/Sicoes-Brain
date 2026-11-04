export const dynamic = 'force-dynamic'

import Link from 'next/link'

import SiteHeader from '@/components/SiteHeader'
import HistSearchList, { type SearchRow } from '@/components/HistSearchList'
import { getHistData, agruparProductos, num, fmtMonto, type HistItem } from '@/lib/historico'

const valItem = (it: HistItem) => num(it.monto_total) || num(it.precio_adjudicado) * num(it.cantidad)

export default async function ProductoIndexPage() {
  const data = await getHistData()
  const grupos = agruparProductos(data.items, data.canonicos)

  const rows: SearchRow[] = Array.from(grupos.values())
    .map((g) => {
      const entidades = new Set(g.items.map((i) => i.entidad_codigo).filter(Boolean)).size
      const monto = g.items.reduce((s, it) => s + valItem(it), 0)
      return { g, entidades, monto }
    })
    .sort((a, b) => b.monto - a.monto)
    .map(({ g, entidades, monto }) => ({
      key: g.key,
      href: `/historico/producto/${encodeURIComponent(g.key)}`,
      label: g.label,
      subtitle: g.unspsc ? `UNSPSC ${g.unspsc}` : null,
      provisional: g.provisional,
      cols: [String(entidades), String(g.items.length), fmtMonto(monto)],
      haystack: `${g.label} ${g.unspsc ?? ''}`.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, ''),
    }))

  return (
    <main className="min-h-screen bg-gray-50">
      <SiteHeader maxWidth="max-w-6xl" />
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 space-y-6">
        <div>
          <Link href="/historico" className="text-xs text-blue-600 hover:underline">← Histórico</Link>
          <div className="flex items-center justify-between gap-4 mt-1">
            <h2 className="text-xl font-bold text-gray-900">Productos (cross-entidad)</h2>
            <Link href="/historico/proveedor" className="text-xs font-medium text-blue-600 hover:underline shrink-0">Ver proveedores →</Link>
          </div>
          <p className="text-xs text-gray-400 mt-0.5">
            Cuánto piden del mismo bien todas las entidades juntas. Escribí para filtrar — también encontrás lo que no aparece en el top.
          </p>
        </div>

        <HistSearchList
          rows={rows}
          colHeaders={['Entidades', 'Ítems', 'Monto']}
          placeholder="Buscar producto o código UNSPSC…"
          unitSingular="producto"
          unitPlural="productos"
        />
      </div>
    </main>
  )
}
