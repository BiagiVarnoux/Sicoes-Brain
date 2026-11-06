export const dynamic = 'force-dynamic'

import Link from 'next/link'

import SiteHeader from '@/components/SiteHeader'
import HistTabs from '@/components/HistTabs'
import HistTimeSeriesChart from '@/components/HistTimeSeriesChart'
import CompararControls from '@/components/CompararControls'
import { StatCard, SectionTitle, Card, RankList, ProvisionalBadge } from '@/components/HistUI'
import {
  getHistData,
  procByCuceMap,
  agruparProductos,
  proveedorKey,
  serieMensual,
  topBy,
  num,
  fmtMonto,
  fmtNum,
  type HistItem,
} from '@/lib/historico'

const MESES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

const valItem = (it: HistItem) => num(it.monto_total) || num(it.precio_adjudicado) * num(it.cantidad)

type Props = { searchParams: Promise<{ producto?: string; entidades?: string }> }

export default async function CompararPage({ searchParams }: Props) {
  const sp = await searchParams
  const selectedProducto = sp.producto ? decodeURIComponent(sp.producto) : null
  const selectedEntidades = (sp.entidades ?? '')
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)

  const data = await getHistData()
  const procByCuce = procByCuceMap(data.procesos)
  const grupos = agruparProductos(data.items, data.canonicos)

  // Opciones de bien (ordenadas por monto, el top primero)
  const productos = Array.from(grupos.values())
    .map((g) => ({ g, monto: g.items.reduce((s, it) => s + valItem(it), 0) }))
    .sort((a, b) => b.monto - a.monto)
    .map(({ g }) => ({ key: g.key, label: g.label, provisional: g.provisional }))

  const grupo = selectedProducto ? grupos.get(selectedProducto) ?? null : null
  const grupoItems = grupo?.items ?? []

  // Entidades que compran este bien (opciones del multi-selector)
  const entStats = new Map<string, { monto: number; items: number }>()
  for (const it of grupoItems) {
    const c = it.entidad_codigo
    if (!c) continue
    const r = entStats.get(c) ?? { monto: 0, items: 0 }
    r.monto += valItem(it)
    r.items += 1
    entStats.set(c, r)
  }
  const entidadOpts = Array.from(entStats.entries())
    .map(([codigo, v]) => ({ codigo, nombre: data.entidadNombre.get(codigo) ?? codigo, monto: v.monto, items: v.items }))
    .sort((a, b) => b.monto - a.monto)

  // Alcance: entidades seleccionadas, o todas las que compran el bien si no hay selección
  const scopeSet = selectedEntidades.length ? new Set(selectedEntidades) : null
  const scoped = scopeSet ? grupoItems.filter((it) => it.entidad_codigo && scopeSet.has(it.entidad_codigo)) : grupoItems

  // Agregado del grupo
  const perEnt = new Map<string, { monto: number; cant: number; items: number }>()
  for (const it of scoped) {
    const c = it.entidad_codigo
    if (!c) continue
    const r = perEnt.get(c) ?? { monto: 0, cant: 0, items: 0 }
    r.monto += valItem(it)
    r.cant += num(it.cantidad)
    r.items += 1
    perEnt.set(c, r)
  }
  const montoTotal = scoped.reduce((s, it) => s + valItem(it), 0)
  const montoEjec = scoped.reduce((s, it) => s + num(it.monto_ejecutado), 0)
  const cantTotal = scoped.reduce((s, it) => s + num(it.cantidad), 0)
  const precioProm = cantTotal > 0 ? montoTotal / cantTotal : null

  // Comparación entidad por entidad (precio unit. = monto/cantidad, efectivo)
  const comp = Array.from(perEnt.entries())
    .map(([codigo, v]) => ({
      codigo,
      nombre: data.entidadNombre.get(codigo) ?? codigo,
      monto: v.monto,
      cant: v.cant,
      items: v.items,
      precio: v.cant > 0 ? v.monto / v.cant : 0,
    }))
    .sort((a, b) => b.monto - a.monto)

  const preciosValidos = comp.map((c) => c.precio).filter((p) => p > 0)
  const precioMin = preciosValidos.length ? Math.min(...preciosValidos) : null
  const precioMax = preciosValidos.length ? Math.max(...preciosValidos) : null

  // Serie mensual del grupo en alcance
  const serie = serieMensual(scoped, procByCuce).map((d) => ({
    label: `${MESES[d.mes - 1]} ${String(d.anio).slice(2)}`,
    valor: d.monto,
  }))

  // Proveedores que venden este bien a las entidades elegidas
  const topProveedores = topBy(scoped, (it) => it.proveedor, valItem, 12).map((r) => ({
    key: proveedorKey(r.key) ?? r.key,
    label: r.key,
    value: r.value,
    sub: `${fmtNum(r.count)} ítem${r.count !== 1 ? 's' : ''}`,
  }))

  // Barras de monto por entidad (ranking visual)
  const rankMonto = comp.map((c) => ({
    key: c.codigo,
    label: c.nombre,
    value: c.monto,
    sub: `${fmtNum(c.items)} ítem${c.items !== 1 ? 's' : ''}`,
  }))

  return (
    <main className="min-h-screen bg-gray-50">
      <SiteHeader maxWidth="max-w-6xl" />
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-6">
        <HistTabs />
        <div>
          <h2 className="text-xl font-bold text-gray-900">Comparar</h2>
          <p className="text-xs text-gray-400 mt-0.5">
            Elegí un bien y una o varias entidades para ver sus estadísticas cruzadas: el grupo en conjunto y cada entidad por separado.
          </p>
        </div>

        <CompararControls
          productos={productos}
          selectedProducto={selectedProducto}
          productoLabel={grupo?.label ?? null}
          productoProvisional={grupo?.provisional}
          entidades={entidadOpts}
          selectedEntidades={selectedEntidades}
        />

        {!selectedProducto ? (
          <div className="bg-white rounded-xl border border-dashed border-gray-200 p-10 text-center text-sm text-gray-400">
            Elegí un bien arriba para empezar.
          </div>
        ) : scoped.length === 0 ? (
          <div className="bg-white rounded-xl border border-gray-200 p-10 text-center text-sm text-gray-400">
            No hay compras para la selección actual.
          </div>
        ) : (
          <>
            <div className="flex items-center gap-2 text-sm text-gray-600 flex-wrap">
              <span className="font-medium text-gray-900 flex items-center gap-1.5">
                {grupo?.label}
                {grupo?.provisional && <ProvisionalBadge />}
              </span>
              <span className="text-gray-400">·</span>
              <span>
                {scopeSet
                  ? `${comp.length} entidad${comp.length !== 1 ? 'es' : ''} seleccionada${comp.length !== 1 ? 's' : ''}`
                  : `todas las entidades (${comp.length})`}
              </span>
            </div>

            {/* Agregado del grupo */}
            <section className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
              <StatCard label="Entidades" value={fmtNum(comp.length)} sub="en el grupo" color="bg-blue-500" />
              <StatCard label="Ítems" value={fmtNum(scoped.length)} sub="compras" color="bg-violet-500" />
              <StatCard label="Cantidad" value={fmtNum(cantTotal)} sub="unidades" color="bg-amber-500" />
              <StatCard label="Monto total" value={fmtMonto(montoTotal)} sub={montoEjec > 0 ? `${Math.round((montoEjec / montoTotal) * 100)}% ejecutado` : undefined} color="bg-emerald-500" />
              <StatCard
                label="Precio unit."
                value={precioProm != null ? fmtMonto(precioProm) : '—'}
                sub={precioMin != null && precioMax != null && precioMin !== precioMax ? `${fmtMonto(precioMin)}–${fmtMonto(precioMax)}` : 'promedio del grupo'}
                color="bg-rose-500"
              />
            </section>

            <section>
              <SectionTitle hint="Monto adjudicado por mes, sumando las entidades elegidas">Evolución mensual del grupo</SectionTitle>
              <Card>{serie.length > 0 ? <HistTimeSeriesChart data={serie} /> : <Empty />}</Card>
            </section>

            {/* Comparación entidad por entidad */}
            <section>
              <SectionTitle hint="Cada entidad por separado · precio unit. = monto / cantidad. El más alto/bajo se resalta.">
                Comparación por entidad
              </SectionTitle>
              <div className="bg-white rounded-xl border border-gray-200 overflow-hidden overflow-x-auto">
                <table className="w-full text-sm min-w-[640px]">
                  <thead>
                    <tr className="border-b border-gray-100 bg-gray-50 text-xs text-gray-500">
                      <th className="text-left px-4 py-3 font-medium">Entidad</th>
                      <th className="text-right px-4 py-3 font-medium">Ítems</th>
                      <th className="text-right px-4 py-3 font-medium">Cantidad</th>
                      <th className="text-right px-4 py-3 font-medium">Monto</th>
                      <th className="text-right px-4 py-3 font-medium">Precio unit.</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {comp.map((c) => {
                      const esMax = precioMax != null && c.precio === precioMax && precioMin !== precioMax
                      const esMin = precioMin != null && c.precio === precioMin && precioMin !== precioMax
                      return (
                        <tr key={c.codigo} className="hover:bg-gray-50 align-top">
                          <td className="px-4 py-3 text-xs max-w-[280px] whitespace-normal break-words leading-tight">
                            <Link href={`/historico/entidad/${encodeURIComponent(c.codigo)}`} className="text-gray-700 hover:text-blue-600 hover:underline">
                              {c.nombre}
                            </Link>
                            <span className="block text-[10px] text-gray-400 mt-0.5">{c.codigo}</span>
                          </td>
                          <td className="px-4 py-3 text-xs text-gray-600 text-right tabular-nums">{fmtNum(c.items)}</td>
                          <td className="px-4 py-3 text-xs text-gray-600 text-right tabular-nums">{fmtNum(c.cant)}</td>
                          <td className="px-4 py-3 text-xs font-semibold text-emerald-700 text-right tabular-nums">{fmtMonto(c.monto)}</td>
                          <td className="px-4 py-3 text-xs text-right tabular-nums">
                            {c.precio > 0 ? (
                              <span className={`inline-flex items-center gap-1 ${esMax ? 'text-rose-600 font-semibold' : esMin ? 'text-emerald-600 font-semibold' : 'text-gray-600'}`}>
                                {fmtMonto(c.precio)}
                                {esMax && <span className="text-[9px] uppercase">máx</span>}
                                {esMin && <span className="text-[9px] uppercase">mín</span>}
                              </span>
                            ) : (
                              '—'
                            )}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </section>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <section>
                <SectionTitle hint="Cuánto gastó cada entidad en el bien · clic para ver la entidad">Monto por entidad</SectionTitle>
                <Card>
                  <RankList rows={rankMonto} hrefOf={(k) => `/historico/entidad/${encodeURIComponent(k)}`} emptyLabel="Sin entidades" />
                </Card>
              </section>
              <section>
                <SectionTitle hint="Quién les vende este bien · clic para ver el proveedor">Proveedores del grupo</SectionTitle>
                <Card>
                  <RankList rows={topProveedores} hrefOf={(k) => `/historico/proveedor/${encodeURIComponent(k)}`} emptyLabel="Sin proveedores" />
                </Card>
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
