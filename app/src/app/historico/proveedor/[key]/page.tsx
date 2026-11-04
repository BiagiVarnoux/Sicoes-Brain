export const dynamic = 'force-dynamic'

import Link from 'next/link'

import SiteHeader from '@/components/SiteHeader'
import HistTimeSeriesChart from '@/components/HistTimeSeriesChart'
import { StatCard, SectionTitle, Card, RankList } from '@/components/HistUI'
import {
  getHistData,
  procByCuceMap,
  proveedorKey,
  productoKey,
  agruparProductos,
  serieMensual,
  topBy,
  num,
  fmtMonto,
  fmtNum,
  type HistItem,
} from '@/lib/historico'

const MESES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

const valItem = (it: HistItem) => num(it.monto_total) || num(it.precio_adjudicado) * num(it.cantidad)

type Props = { params: Promise<{ key: string }> }

export default async function ProveedorHistoricoPage({ params }: Props) {
  const { key: raw } = await params
  const key = decodeURIComponent(raw)

  const data = await getHistData()
  const procByCuce = procByCuceMap(data.procesos)

  const items = data.items.filter((it) => proveedorKey(it.proveedor) === key)

  // Nombre representativo (el más frecuente escrito para este proveedor)
  const freq = new Map<string, number>()
  for (const it of items) {
    const d = (it.proveedor ?? '').trim()
    if (d) freq.set(d, (freq.get(d) ?? 0) + 1)
  }
  const label = [...freq.entries()].sort((a, b) => b[1] - a[1] || b[0].length - a[0].length)[0]?.[0] ?? '(proveedor)'

  const montoAdj = items.reduce((s, it) => s + valItem(it), 0)
  const montoEjec = items.reduce((s, it) => s + num(it.monto_ejecutado), 0)
  const entidades = new Set(items.map((it) => it.entidad_codigo).filter(Boolean))
  const grupos = agruparProductos(items, data.canonicos)

  const serie = serieMensual(items, procByCuce).map((d) => ({
    label: `${MESES[d.mes - 1]} ${String(d.anio).slice(2)}`,
    valor: d.monto,
  }))

  // Entidades a las que les vende
  const topEntidades = topBy(items, (it) => it.entidad_codigo, valItem, 12).map((r) => ({
    key: r.key,
    label: data.entidadNombre.get(r.key) ?? r.key,
    value: r.value,
    sub: `${fmtNum(r.count)} ítem${r.count !== 1 ? 's' : ''}`,
  }))

  // Productos que provee
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

  // Detalle de contratos
  const filas = items
    .map((it) => ({
      entidad: data.entidadNombre.get(it.entidad_codigo ?? '') ?? it.entidad_codigo ?? '—',
      entidadCodigo: it.entidad_codigo ?? '',
      fecha: it.fecha_publicacion ?? procByCuce.get(it.cuce)?.fecha_publicacion ?? null,
      producto: (it.descripcion ?? '').trim() || '—',
      productoHref: `/historico/producto/${encodeURIComponent(productoKey(it))}`,
      cantidad: num(it.cantidad),
      unidad: it.unidad_medida,
      monto: valItem(it),
    }))
    .sort((a, b) => (b.fecha ?? '').localeCompare(a.fecha ?? ''))

  const notFound = items.length === 0

  return (
    <main className="min-h-screen bg-gray-50">
      <SiteHeader maxWidth="max-w-6xl" />
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 space-y-6">
        <div>
          <Link href="/historico/proveedor" className="text-xs text-blue-600 hover:underline">← Proveedores</Link>
          <h2 className="text-xl font-bold text-gray-900 mt-1">{label}</h2>
          <p className="text-xs text-gray-400 mt-0.5">Qué provee y a qué entidades, en el tiempo</p>
        </div>

        {notFound ? (
          <div className="bg-white rounded-xl border border-gray-200 p-10 text-center text-sm text-gray-400">
            No hay datos para este proveedor.
          </div>
        ) : (
          <>
            <section className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
              <StatCard label="Entidades" value={fmtNum(entidades.size)} sub="a las que vende" color="bg-blue-500" />
              <StatCard label="Productos" value={fmtNum(grupos.size)} sub="bienes distintos" color="bg-amber-500" />
              <StatCard label="Ítems" value={fmtNum(items.length)} sub="líneas adjudicadas" color="bg-violet-500" />
              <StatCard label="Adjudicado" value={fmtMonto(montoAdj)} color="bg-emerald-500" />
              <StatCard label="Ejecutado" value={fmtMonto(montoEjec)} sub={montoAdj > 0 ? `${Math.round((montoEjec / montoAdj) * 100)}% del adj.` : undefined} color="bg-teal-500" />
            </section>

            <section>
              <SectionTitle hint="Monto adjudicado por mes de publicación">Evolución mensual</SectionTitle>
              <Card>{serie.length > 0 ? <HistTimeSeriesChart data={serie} /> : <Empty />}</Card>
            </section>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <section>
                <SectionTitle hint="A quién le vende más · clic para ver la entidad">Entidades que le compran</SectionTitle>
                <Card>
                  <RankList rows={topEntidades} hrefOf={(k) => `/historico/entidad/${encodeURIComponent(k)}`} emptyLabel="Sin entidades" />
                </Card>
              </section>
              <section>
                <SectionTitle hint="Qué provee más · clic para ver cross-entidad">Productos que provee</SectionTitle>
                <Card>
                  <RankList rows={topProductos} hrefOf={(k) => `/historico/producto/${encodeURIComponent(k)}`} emptyLabel="Sin productos" />
                </Card>
              </section>
            </div>

            <section>
              <SectionTitle hint="Todos los contratos adjudicados a este proveedor">Detalle de contratos</SectionTitle>
              <div className="bg-white rounded-xl border border-gray-200 overflow-hidden overflow-x-auto">
                <table className="w-full text-sm min-w-[640px]">
                  <thead>
                    <tr className="border-b border-gray-100 bg-gray-50 text-xs text-gray-500">
                      <th className="text-left px-4 py-3 font-medium">Entidad</th>
                      <th className="text-left px-4 py-3 font-medium">Fecha</th>
                      <th className="text-left px-4 py-3 font-medium">Producto</th>
                      <th className="text-right px-4 py-3 font-medium">Cantidad</th>
                      <th className="text-right px-4 py-3 font-medium">Monto</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {filas.map((f, i) => (
                      <tr key={i} className="hover:bg-gray-50 align-top">
                        <td className="px-4 py-3 text-xs text-gray-700 max-w-[240px] whitespace-normal break-words leading-tight">
                          {f.entidad}
                          {f.entidadCodigo && <span className="block text-[10px] text-gray-400 mt-0.5">{f.entidadCodigo}</span>}
                        </td>
                        <td className="px-4 py-3 text-xs text-gray-500 tabular-nums">{f.fecha ?? '—'}</td>
                        <td className="px-4 py-3 text-xs max-w-[280px]">
                          <Link href={f.productoHref} className="text-gray-700 hover:text-blue-600 line-clamp-2 leading-tight">{f.producto}</Link>
                        </td>
                        <td className="px-4 py-3 text-xs text-gray-600 text-right tabular-nums">
                          {fmtNum(f.cantidad)}{f.unidad ? ` ${f.unidad}` : ''}
                        </td>
                        <td className="px-4 py-3 text-xs font-semibold text-emerald-700 text-right tabular-nums">{fmtMonto(f.monto)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        )}
      </div>
    </main>
  )
}

function Empty() {
  return <div className="h-[200px] flex items-center justify-center text-sm text-gray-400">Sin datos</div>
}
