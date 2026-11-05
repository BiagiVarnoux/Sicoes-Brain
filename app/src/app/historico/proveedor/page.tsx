export const dynamic = 'force-dynamic'

import SiteHeader from '@/components/SiteHeader'
import HistTabs from '@/components/HistTabs'
import HistSearchList, { type SearchRow } from '@/components/HistSearchList'
import { getHistData, agruparProveedores, num, fmtMonto, type HistItem } from '@/lib/historico'

const valItem = (it: HistItem) => num(it.monto_total) || num(it.precio_adjudicado) * num(it.cantidad)

export default async function ProveedorIndexPage() {
  const data = await getHistData()
  const grupos = agruparProveedores(data.items)

  const rows: SearchRow[] = Array.from(grupos.values())
    .map((g) => {
      const entidades = new Set(g.items.map((i) => i.entidad_codigo).filter(Boolean)).size
      const monto = g.items.reduce((s, it) => s + valItem(it), 0)
      return { g, entidades, monto }
    })
    .sort((a, b) => b.monto - a.monto)
    .map(({ g, entidades, monto }) => ({
      key: g.key,
      href: `/historico/proveedor/${encodeURIComponent(g.key)}`,
      label: g.label,
      subtitle: null,
      cols: [String(entidades), String(g.items.length), fmtMonto(monto)],
      haystack: g.label.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, ''),
    }))

  return (
    <main className="min-h-screen bg-gray-50">
      <SiteHeader maxWidth="max-w-6xl" />
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-6">
        <HistTabs />
        <div>
          <h2 className="text-xl font-bold text-gray-900">Proveedores</h2>
          <p className="text-xs text-gray-400 mt-0.5">
            Quién gana los contratos del Estado. Escribí para filtrar — también encontrás a quienes no aparecen en el top.
          </p>
        </div>

        <HistSearchList
          rows={rows}
          colHeaders={['Entidades', 'Ítems', 'Monto']}
          placeholder="Buscar proveedor…"
          unitSingular="proveedor"
          unitPlural="proveedores"
        />
      </div>
    </main>
  )
}
