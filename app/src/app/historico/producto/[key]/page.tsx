export const dynamic = 'force-dynamic'

import Link from 'next/link'

import SiteHeader from '@/components/SiteHeader'
import HistTimeSeriesChart from '@/components/HistTimeSeriesChart'
import HistPrecioChart from '@/components/HistPrecioChart'
import { StatCard, SectionTitle, Card, RankList, ProvisionalBadge } from '@/components/HistUI'
import {
  getHistData,
  procByCuceMap,
  productoKey,
  serieMensual,
  proyectarAnual,
  budgetPorAnio,
  topBy,
  num,
  fmtMonto,
  fmtNum,
  type HistItem,
} from '@/lib/historico'

const MESES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

const valItem = (it: HistItem) => num(it.monto_total) || num(it.precio_adjudicado) * num(it.cantidad)
const precioUnit = (it: HistItem) => num(it.precio_adjudicado) || (num(it.cantidad) ? valItem(it) / num(it.cantidad) : 0)

type Props = { params: Promise<{ key: string }> }

export default async function ProductoHistoricoPage({ params }: Props) {
  const { key: raw } = await params
  const key = decodeURIComponent(raw)

  const data = await getHistData()
  const procByCuce = procByCuceMap(data.procesos)

  const items = data.items.filter((it) => productoKey(it) === key)

  // Etiqueta / metadata del grupo
  const provisional = !key.startsWith('c:')
  let label = '(producto)'
  let unspsc: string | null = null
  if (key.startsWith('c:')) {
    const c = data.canonicos.get(Number(key.slice(2)))
    label = c?.nombre_canonico ?? items[0]?.descripcion ?? label
    unspsc = c?.unspsc_codigo ?? items[0]?.unspsc_codigo ?? null
  } else {
    // descripción más frecuente
    const freq = new Map<string, number>()
    for (const it of items) {
      const d = (it.descripcion ?? '').trim()
      if (d) freq.set(d, (freq.get(d) ?? 0) + 1)
    }
    label = [...freq.entries()].sort((a, b) => b[1] - a[1] || b[0].length - a[0].length)[0]?.[0] ?? label
    unspsc = items[0]?.unspsc_codigo ?? null
  }

  const montoTotal = items.reduce((s, it) => s + valItem(it), 0)
  const cantidadTotal = items.reduce((s, it) => s + num(it.cantidad), 0)
  const entidades = new Set(items.map((it) => it.entidad_codigo).filter(Boolean))
  const precios = items.map(precioUnit).filter((p) => p > 0)
  const precioMin = precios.length ? Math.min(...precios) : null
  const precioMax = precios.length ? Math.max(...precios) : null
  const precioProm = precios.length ? precios.reduce((s, p) => s + p, 0) / precios.length : null

  // Serie mensual agregada (todas las entidades)
  const serie = serieMensual(items, procByCuce).map((d) => ({
    label: `${MESES[d.mes - 1]} ${String(d.anio).slice(2)}`,
    valor: d.monto,
  }))

  // Proyección de demanda agregada (cantidad anual)
  const cantAnual = new Map<number, number>()
  for (const it of items) {
    const a = num(it.fecha_publicacion ? Number(it.fecha_publicacion.slice(0, 4)) : 0) || procByCuce.get(it.cuce)?.cuce_anio || 0
    if (a) cantAnual.set(a, (cantAnual.get(a) ?? 0) + num(it.cantidad))
  }
  const proy = proyectarAnual([...cantAnual.entries()].map(([anio, valor]) => ({ anio, valor })))
  const serieAnual = proy
    ? [
        ...proy.base.map((p) => ({ label: String(p.anio), valor: p.valor, proyeccion: false })),
        { label: `${proy.nextAnio}*`, valor: proy.nextValor, proyeccion: true },
      ]
    : []

  // Ranking de entidades que más lo compran
  const topEntidades = topBy(items, (it) => it.entidad_codigo, valItem, 12).map((r) => ({
    key: r.key,
    label: data.entidadNombre.get(r.key) ?? r.key,
    value: r.value,
    sub: `${fmtNum(r.count)} ítem${r.count !== 1 ? 's' : ''}`,
  }))

  // Dispersión de precios por entidad
  const dispersion = items
    .map((it) => ({
      fecha: it.fecha_publicacion ?? procByCuce.get(it.cuce)?.fecha_publicacion ?? '',
      precio: precioUnit(it),
      entidad: data.entidadNombre.get(it.entidad_codigo ?? '') ?? it.entidad_codigo ?? '—',
      cantidad: num(it.cantidad),
    }))
    .filter((d) => d.fecha && d.precio > 0)

  // Tabla de ítems
  const filas = items
    .map((it) => ({
      cuce: it.cuce,
      entidad: data.entidadNombre.get(it.entidad_codigo ?? '') ?? it.entidad_codigo ?? '—',
      fecha: it.fecha_publicacion ?? procByCuce.get(it.cuce)?.fecha_publicacion ?? null,
      cantidad: num(it.cantidad),
      unidad: it.unidad_medida,
      precio: precioUnit(it),
      monto: valItem(it),
      proveedor: it.proveedor,
    }))
    .sort((a, b) => (b.fecha ?? '').localeCompare(a.fecha ?? ''))

  const notFound = items.length === 0

  return (
    <main className="min-h-screen bg-gray-50">
      <SiteHeader maxWidth="max-w-6xl" />
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 space-y-6">
        <div>
          <Link href="/historico/producto" className="text-xs text-blue-600 hover:underline">← Productos</Link>
          <h2 className="text-xl font-bold text-gray-900 mt-1 flex items-center gap-2">
            {label}
            {provisional && <ProvisionalBadge />}
          </h2>
          <p className="text-xs text-gray-400 mt-0.5">
            Análisis cross-entidad{unspsc ? ` · UNSPSC ${unspsc}` : ''}
          </p>
        </div>

        {notFound ? (
          <div className="bg-white rounded-xl border border-gray-200 p-10 text-center text-sm text-gray-400">
            No hay datos para este producto.
          </div>
        ) : (
          <>
            {provisional && (
              <div className="flex items-start gap-2 text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded-xl px-4 py-3">
                <ProvisionalBadge />
                <span>
                  Agrupación aproximada por {key.startsWith('u:') ? 'código UNSPSC' : 'descripción'}. Puede juntar o
                  separar bienes que la canonicalización por IA consolidará distinto.
                </span>
              </div>
            )}

            <section className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
              <StatCard label="Entidades" value={fmtNum(entidades.size)} sub="que lo compran" color="bg-blue-500" />
              <StatCard label="Ítems" value={fmtNum(items.length)} sub="compras registradas" color="bg-violet-500" />
              <StatCard label="Cantidad" value={fmtNum(cantidadTotal)} sub="unidades" color="bg-amber-500" />
              <StatCard label="Monto total" value={fmtMonto(montoTotal)} color="bg-emerald-500" />
              <StatCard
                label="Precio unit."
                value={precioProm != null ? fmtMonto(precioProm) : '—'}
                sub={precioMin != null && precioMax != null && precioMin !== precioMax ? `${fmtMonto(precioMin)}–${fmtMonto(precioMax)}` : 'promedio'}
                color="bg-rose-500"
              />
            </section>

            <section>
              <SectionTitle hint="Cada punto es una compra; el color es la entidad. Muestra cuánto varía el precio entre entidades.">
                Dispersión de precios por entidad
              </SectionTitle>
              <Card>{dispersion.length > 0 ? <HistPrecioChart data={dispersion} /> : <Empty />}</Card>
            </section>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <section>
                <SectionTitle hint="Clic para ver el detalle de la entidad">Entidades que más lo compran</SectionTitle>
                <Card>
                  <RankList rows={topEntidades} hrefOf={(k) => `/historico/entidad/${encodeURIComponent(k)}`} emptyLabel="Sin entidades" />
                </Card>
              </section>
              <section>
                <SectionTitle hint="Monto adjudicado agregado por mes (todas las entidades)">Evolución mensual</SectionTitle>
                <Card>{serie.length > 0 ? <HistTimeSeriesChart data={serie} /> : <Empty />}</Card>
              </section>
            </div>

            {proy && (
              <section>
                <SectionTitle hint={`Demanda agregada (unidades/año) · tendencia lineal · R²=${proy.r2.toFixed(2)}`}>
                  Proyección de demanda {proy.nextAnio}
                </SectionTitle>
                <Card right={<span className="text-xs text-gray-400">estimado: <span className="font-semibold text-blue-600">{fmtNum(proy.nextValor)} u.</span></span>}>
                  <HistTimeSeriesChart data={serieAnual} firstProjIndex={serieAnual.length - 1} unidad="u." />
                </Card>
              </section>
            )}

            <section>
              <SectionTitle hint="Todas las compras del producto, cross-entidad">Detalle de compras</SectionTitle>
              <div className="bg-white rounded-xl border border-gray-200 overflow-hidden overflow-x-auto">
                <table className="w-full text-sm min-w-[640px]">
                  <thead>
                    <tr className="border-b border-gray-100 bg-gray-50 text-xs text-gray-500">
                      <th className="text-left px-4 py-3 font-medium">Entidad</th>
                      <th className="text-left px-4 py-3 font-medium">Fecha</th>
                      <th className="text-right px-4 py-3 font-medium">Cantidad</th>
                      <th className="text-right px-4 py-3 font-medium">Precio unit.</th>
                      <th className="text-right px-4 py-3 font-medium">Monto</th>
                      <th className="text-left px-4 py-3 font-medium">Proveedor</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {filas.map((f, i) => (
                      <tr key={i} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-xs text-gray-700 max-w-[200px] truncate">{f.entidad}</td>
                        <td className="px-4 py-3 text-xs text-gray-500 tabular-nums">{f.fecha ?? '—'}</td>
                        <td className="px-4 py-3 text-xs text-gray-600 text-right tabular-nums">
                          {fmtNum(f.cantidad)}{f.unidad ? ` ${f.unidad}` : ''}
                        </td>
                        <td className="px-4 py-3 text-xs text-gray-600 text-right tabular-nums">{f.precio > 0 ? fmtMonto(f.precio) : '—'}</td>
                        <td className="px-4 py-3 text-xs font-semibold text-emerald-700 text-right tabular-nums">{fmtMonto(f.monto)}</td>
                        <td className="px-4 py-3 text-xs text-gray-500 max-w-[200px] truncate">{f.proveedor ?? '—'}</td>
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
