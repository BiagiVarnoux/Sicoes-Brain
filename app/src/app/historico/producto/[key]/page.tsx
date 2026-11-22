export const dynamic = 'force-dynamic'

import Link from 'next/link'

import SiteHeader from '@/components/SiteHeader'
import HistTabs from '@/components/HistTabs'
import HistTimeSeriesChart from '@/components/HistTimeSeriesChart'
import HistPrecioChart from '@/components/HistPrecioChart'
import HistSeasonalityChart from '@/components/HistSeasonalityChart'
import ProductoControls from '@/components/ProductoControls'
import { StatCard, SectionTitle, Card, RankList, ProvisionalBadge } from '@/components/HistUI'
import {
  getHistData,
  procByCuceMap,
  productoKey,
  proveedorKey,
  itemAnio,
  serieMensual,
  estacionalidad,
  proyectarAnual,
  topBy,
  num,
  fmtMonto,
  fmtNum,
  type HistItem,
} from '@/lib/historico'

const MESES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

const valItem = (it: HistItem) => num(it.monto_total) || num(it.precio_adjudicado) * num(it.cantidad)
const precioUnit = (it: HistItem) => num(it.precio_adjudicado) || (num(it.cantidad) ? valItem(it) / num(it.cantidad) : 0)

function fmtIntervalo(dias: number): string {
  if (dias >= 60) return `~${Math.round(dias / 30.44)} meses`
  return `~${Math.round(dias)} días`
}

type Props = {
  params: Promise<{ key: string }>
  searchParams: Promise<{ entidades?: string; anios?: string }>
}

export default async function ProductoHistoricoPage({ params, searchParams }: Props) {
  const { key: raw } = await params
  const key = decodeURIComponent(raw)
  const sp = await searchParams

  const selectedEntidades = (sp.entidades ?? '').split(',').map((s) => s.trim()).filter(Boolean)
  const selectedAnios = (sp.anios ?? '')
    .split(',')
    .map((s) => parseInt(s.trim(), 10))
    .filter((n) => Number.isFinite(n))

  const data = await getHistData()
  const procByCuce = procByCuceMap(data.procesos)

  const allItems = data.items.filter((it) => productoKey(it) === key)

  // Etiqueta / metadata del grupo
  const provisional = !key.startsWith('c:')
  let label = '(producto)'
  let unspsc: string | null = null
  if (key.startsWith('c:')) {
    const c = data.canonicos.get(Number(key.slice(2)))
    label = c?.nombre_canonico ?? allItems[0]?.descripcion ?? label
    unspsc = c?.unspsc_codigo ?? allItems[0]?.unspsc_codigo ?? null
  } else {
    const freq = new Map<string, number>()
    for (const it of allItems) {
      const d = (it.descripcion ?? '').trim()
      if (d) freq.set(d, (freq.get(d) ?? 0) + 1)
    }
    label = [...freq.entries()].sort((a, b) => b[1] - a[1] || b[0].length - a[0].length)[0]?.[0] ?? label
    unspsc = allItems[0]?.unspsc_codigo ?? null
  }

  // Opciones de filtro (sobre todo el universo del bien, no sobre lo filtrado)
  const entStats = new Map<string, { monto: number; items: number }>()
  const anioStats = new Map<number, { monto: number; items: number }>()
  for (const it of allItems) {
    if (it.entidad_codigo) {
      const r = entStats.get(it.entidad_codigo) ?? { monto: 0, items: 0 }
      r.monto += valItem(it)
      r.items += 1
      entStats.set(it.entidad_codigo, r)
    }
    const a = itemAnio(it, procByCuce)
    if (a) {
      const r = anioStats.get(a) ?? { monto: 0, items: 0 }
      r.monto += valItem(it)
      r.items += 1
      anioStats.set(a, r)
    }
  }
  const entidadOpts = Array.from(entStats.entries())
    .map(([codigo, v]) => ({ codigo, nombre: data.entidadNombre.get(codigo) ?? codigo, monto: v.monto, items: v.items }))
    .sort((a, b) => b.monto - a.monto)
  const anioOpts = Array.from(anioStats.entries())
    .map(([anio, v]) => ({ anio, monto: v.monto, items: v.items }))
    .sort((a, b) => b.anio - a.anio)

  // Alcance filtrado (entidad × año)
  const entSet = selectedEntidades.length ? new Set(selectedEntidades) : null
  const anioSet = selectedAnios.length ? new Set(selectedAnios) : null
  const items = allItems.filter((it) => {
    if (entSet && !(it.entidad_codigo && entSet.has(it.entidad_codigo))) return false
    if (anioSet) {
      const a = itemAnio(it, procByCuce)
      if (a == null || !anioSet.has(a)) return false
    }
    return true
  })

  const hayFiltro = selectedEntidades.length > 0 || selectedAnios.length > 0

  // ── Agregados ──────────────────────────────────────────────────────────────
  const montoTotal = items.reduce((s, it) => s + valItem(it), 0)
  const montoEjec = items.reduce((s, it) => s + num(it.monto_ejecutado), 0)
  const cantidadTotal = items.reduce((s, it) => s + num(it.cantidad), 0)
  const entidadesEnScope = new Set(items.map((it) => it.entidad_codigo).filter(Boolean))
  const precios = items.map(precioUnit).filter((p) => p > 0)
  const precioMin = precios.length ? Math.min(...precios) : null
  const precioMax = precios.length ? Math.max(...precios) : null
  const precioProm = cantidadTotal > 0 ? montoTotal / cantidadTotal : null

  // ── Procesos (CUCE distintos) en el alcance ────────────────────────────────
  const procMap = new Map<
    string,
    { cuce: string; fecha: string | null; entidad: string; entidadCodigo: string; modalidad: string | null; cant: number; monto: number }
  >()
  for (const it of items) {
    const p = procByCuce.get(it.cuce)
    const r = procMap.get(it.cuce) ?? {
      cuce: it.cuce,
      fecha: it.fecha_publicacion ?? p?.fecha_publicacion ?? null,
      entidad: data.entidadNombre.get(it.entidad_codigo ?? '') ?? it.entidad_codigo ?? '—',
      entidadCodigo: it.entidad_codigo ?? '',
      modalidad: p?.modalidad ?? it.modalidad ?? null,
      cant: 0,
      monto: 0,
    }
    r.cant += num(it.cantidad)
    r.monto += valItem(it)
    procMap.set(it.cuce, r)
  }
  const procesos = Array.from(procMap.values()).sort((a, b) => (b.fecha ?? '').localeCompare(a.fecha ?? ''))

  // ── Ritmo de pedido ────────────────────────────────────────────────────────
  const fechasPedido = procesos.map((p) => p.fecha).filter((f): f is string => !!f).sort()
  let intervaloProm: number | null = null
  if (fechasPedido.length >= 2) {
    const difs: number[] = []
    for (let i = 1; i < fechasPedido.length; i++) {
      const d = (new Date(fechasPedido[i]).getTime() - new Date(fechasPedido[i - 1]).getTime()) / 86_400_000
      if (Number.isFinite(d)) difs.push(d)
    }
    intervaloProm = difs.length ? difs.reduce((s, d) => s + d, 0) / difs.length : null
  }
  const ultimoPedido = fechasPedido.length ? fechasPedido[fechasPedido.length - 1] : null
  const primerPedido = fechasPedido.length ? fechasPedido[0] : null

  // ── Pedidos por año (cantidad + monto) — "cuánto se pidió el último año" ────
  const porAnio = new Map<number, { cant: number; monto: number; pedidos: Set<string> }>()
  for (const it of items) {
    const a = itemAnio(it, procByCuce)
    if (!a) continue
    const r = porAnio.get(a) ?? { cant: 0, monto: 0, pedidos: new Set<string>() }
    r.cant += num(it.cantidad)
    r.monto += valItem(it)
    r.pedidos.add(it.cuce)
    porAnio.set(a, r)
  }
  const filasAnio = Array.from(porAnio.entries())
    .map(([anio, v]) => ({ anio, cant: v.cant, monto: v.monto, pedidos: v.pedidos.size }))
    .sort((a, b) => b.anio - a.anio)
  const anioMax = filasAnio.length ? Math.max(...filasAnio.map((f) => f.anio)) : null

  // ── Proyección de demanda (cantidad anual) ─────────────────────────────────
  const proy = proyectarAnual(filasAnio.map((f) => ({ anio: f.anio, valor: f.cant })))
  const serieAnual = proy
    ? [
        ...proy.base.map((p) => ({ label: String(p.anio), valor: p.valor, proyeccion: false })),
        { label: `${proy.nextAnio}*`, valor: proy.nextValor, proyeccion: true },
      ]
    : []

  // ── Serie mensual ──────────────────────────────────────────────────────────
  const serie = serieMensual(items, procByCuce).map((d) => ({
    label: `${MESES[d.mes - 1]} ${String(d.anio).slice(2)}`,
    valor: d.monto,
  }))

  // ── Estacionalidad ─────────────────────────────────────────────────────────
  const season = estacionalidad(items, procByCuce, 'entrega')

  // ── Comparación por entidad ────────────────────────────────────────────────
  const perEnt = new Map<string, { monto: number; cant: number; items: number }>()
  for (const it of items) {
    const c = it.entidad_codigo
    if (!c) continue
    const r = perEnt.get(c) ?? { monto: 0, cant: 0, items: 0 }
    r.monto += valItem(it)
    r.cant += num(it.cantidad)
    r.items += 1
    perEnt.set(c, r)
  }
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
  const preciosComp = comp.map((c) => c.precio).filter((p) => p > 0)
  const compMin = preciosComp.length ? Math.min(...preciosComp) : null
  const compMax = preciosComp.length ? Math.max(...preciosComp) : null

  // ── Rankings ───────────────────────────────────────────────────────────────
  const topEntidades = topBy(items, (it) => it.entidad_codigo, valItem, 12).map((r) => ({
    key: r.key,
    label: data.entidadNombre.get(r.key) ?? r.key,
    value: r.value,
    sub: `${fmtNum(r.count)} ítem${r.count !== 1 ? 's' : ''}`,
  }))
  const topProveedores = topBy(items, (it) => it.proveedor, valItem, 12).map((r) => ({
    key: proveedorKey(r.key) ?? r.key,
    label: r.key,
    value: r.value,
    sub: `${fmtNum(r.count)} ítem${r.count !== 1 ? 's' : ''}`,
  }))
  const rankMonto = comp.map((c) => ({
    key: c.codigo,
    label: c.nombre,
    value: c.monto,
    sub: `${fmtNum(c.items)} ítem${c.items !== 1 ? 's' : ''}`,
  }))

  // ── Dispersión de precios ──────────────────────────────────────────────────
  const dispersion = items
    .map((it) => ({
      fecha: it.fecha_publicacion ?? procByCuce.get(it.cuce)?.fecha_publicacion ?? '',
      precio: precioUnit(it),
      entidad: data.entidadNombre.get(it.entidad_codigo ?? '') ?? it.entidad_codigo ?? '—',
      cantidad: num(it.cantidad),
    }))
    .filter((d) => d.fecha && d.precio > 0)

  // ── Detalle de compras ─────────────────────────────────────────────────────
  const filas = items
    .map((it) => ({
      cuce: it.cuce,
      entidad: data.entidadNombre.get(it.entidad_codigo ?? '') ?? it.entidad_codigo ?? '—',
      entidadCodigo: it.entidad_codigo ?? '',
      fecha: it.fecha_publicacion ?? procByCuce.get(it.cuce)?.fecha_publicacion ?? null,
      cantidad: num(it.cantidad),
      unidad: it.unidad_medida,
      precio: precioUnit(it),
      monto: valItem(it),
      proveedor: it.proveedor,
      proveedorHref: it.proveedor ? `/historico/proveedor/${encodeURIComponent(proveedorKey(it.proveedor) ?? '')}` : null,
    }))
    .sort((a, b) => (b.fecha ?? '').localeCompare(a.fecha ?? ''))

  const notFound = allItems.length === 0
  const scopeVacio = !notFound && items.length === 0
  const multiEnt = comp.length > 1

  return (
    <main className="min-h-screen bg-gray-50">
      <SiteHeader maxWidth="max-w-6xl" />
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-6">
        <HistTabs />
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

            <ProductoControls
              entidades={entidadOpts}
              selectedEntidades={selectedEntidades}
              anios={anioOpts}
              selectedAnios={selectedAnios}
            />

            {hayFiltro && (
              <div className="flex items-center gap-2 text-sm text-gray-600 flex-wrap">
                <span>
                  {entSet ? `${selectedEntidades.length} entidad${selectedEntidades.length !== 1 ? 'es' : ''}` : 'todas las entidades'}
                </span>
                <span className="text-gray-400">·</span>
                <span>{anioSet ? [...selectedAnios].sort((a, b) => a - b).join(', ') : 'todos los años'}</span>
              </div>
            )}

            {scopeVacio ? (
              <div className="bg-white rounded-xl border border-gray-200 p-10 text-center text-sm text-gray-400">
                No hay compras para la selección actual.
              </div>
            ) : (
              <>
                <section className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
                  <StatCard label="Entidades" value={fmtNum(entidadesEnScope.size)} sub="que lo compran" color="bg-blue-500" />
                  <StatCard label="Ítems" value={fmtNum(items.length)} sub="compras registradas" color="bg-violet-500" />
                  <StatCard label="Cantidad" value={fmtNum(cantidadTotal)} sub="unidades" color="bg-amber-500" />
                  <StatCard
                    label="Monto total"
                    value={fmtMonto(montoTotal)}
                    sub={montoEjec > 0 ? `${Math.round((montoEjec / montoTotal) * 100)}% ejecutado` : undefined}
                    color="bg-emerald-500"
                  />
                  <StatCard
                    label="Precio unit."
                    value={precioProm != null ? fmtMonto(precioProm) : '—'}
                    sub={precioMin != null && precioMax != null && precioMin !== precioMax ? `${fmtMonto(precioMin)}–${fmtMonto(precioMax)}` : 'promedio'}
                    color="bg-rose-500"
                  />
                </section>

                {/* Ritmo de pedido */}
                <section>
                  <SectionTitle hint={multiEnt ? 'Cada cuánto se pide este bien en el alcance' : 'Cada cuánto se pide este bien'}>
                    Ritmo de pedido
                  </SectionTitle>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                    <StatCard label="Pedidos" value={fmtNum(procesos.length)} sub="procesos distintos" color="bg-indigo-500" />
                    <StatCard label="Frecuencia" value={intervaloProm != null ? fmtIntervalo(intervaloProm) : '—'} sub={intervaloProm != null ? 'entre pedidos' : 'un solo pedido'} color="bg-cyan-500" />
                    <StatCard label="Primer pedido" value={primerPedido ?? '—'} color="bg-gray-400" />
                    <StatCard label="Último pedido" value={ultimoPedido ?? '—'} color="bg-teal-500" />
                  </div>
                </section>

                {/* Pedidos por año */}
                {filasAnio.length > 0 && (
                  <section>
                    <SectionTitle hint="Cuánto se pidió del bien cada año (unidades y monto). El último año se resalta.">
                      Pedidos por año
                    </SectionTitle>
                    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden overflow-x-auto">
                      <table className="w-full text-sm min-w-[480px]">
                        <thead>
                          <tr className="border-b border-gray-100 bg-gray-50 text-xs text-gray-500">
                            <th className="text-left px-4 py-3 font-medium">Año</th>
                            <th className="text-right px-4 py-3 font-medium">Pedidos</th>
                            <th className="text-right px-4 py-3 font-medium">Cantidad</th>
                            <th className="text-right px-4 py-3 font-medium">Monto</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-50">
                          {filasAnio.map((f) => (
                            <tr key={f.anio} className={`hover:bg-gray-50 ${f.anio === anioMax ? 'bg-blue-50/40' : ''}`}>
                              <td className="px-4 py-3 text-xs font-semibold text-gray-800 tabular-nums">
                                {f.anio}
                                {f.anio === anioMax && <span className="ml-1.5 text-[9px] uppercase text-blue-600">último</span>}
                              </td>
                              <td className="px-4 py-3 text-xs text-gray-600 text-right tabular-nums">{fmtNum(f.pedidos)}</td>
                              <td className="px-4 py-3 text-xs text-gray-600 text-right tabular-nums">{fmtNum(f.cant)}</td>
                              <td className="px-4 py-3 text-xs font-semibold text-emerald-700 text-right tabular-nums">{fmtMonto(f.monto)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </section>
                )}

                {/* Proyección de demanda */}
                {proy && (
                  <section>
                    <SectionTitle hint={`Demanda (unidades/año) · tendencia lineal · R²=${proy.r2.toFixed(2)}`}>
                      Proyección de demanda {proy.nextAnio}
                    </SectionTitle>
                    <Card right={<span className="text-xs text-gray-400">estimado: <span className="font-semibold text-blue-600">{fmtNum(proy.nextValor)} u.</span></span>}>
                      <HistTimeSeriesChart data={serieAnual} firstProjIndex={serieAnual.length - 1} unidad="u." />
                    </Card>
                  </section>
                )}

                {/* Evolución mensual */}
                <section>
                  <SectionTitle hint="Monto adjudicado agregado por mes">Evolución mensual</SectionTitle>
                  <Card>{serie.length > 0 ? <HistTimeSeriesChart data={serie} /> : <Empty />}</Card>
                </section>

                {/* Estacionalidad */}
                <section>
                  <SectionTitle hint="Por mes de entrega (FORM500) — en qué época se concentran las entregas">Estacionalidad</SectionTitle>
                  <Card>{season.some((s) => s.monto > 0) ? <HistSeasonalityChart data={season} campo="entrega" /> : <Empty />}</Card>
                </section>

                {/* Dispersión de precios */}
                <section>
                  <SectionTitle hint="Cada punto es una compra; el color es la entidad. Muestra cuánto varía el precio entre entidades.">
                    Dispersión de precios por entidad
                  </SectionTitle>
                  <Card>{dispersion.length > 0 ? <HistPrecioChart data={dispersion} /> : <Empty />}</Card>
                </section>

                {/* Comparación por entidad */}
                {multiEnt && (
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
                            const esMax = compMax != null && c.precio === compMax && compMin !== compMax
                            const esMin = compMin != null && c.precio === compMin && compMin !== compMax
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
                )}

                {/* Rankings */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <section>
                    <SectionTitle hint="Clic para ver el detalle de la entidad">Entidades que más lo compran</SectionTitle>
                    <Card>
                      <RankList rows={topEntidades} hrefOf={(k) => `/historico/entidad/${encodeURIComponent(k)}`} emptyLabel="Sin entidades" />
                    </Card>
                  </section>
                  <section>
                    <SectionTitle hint="Quién lo adjudica · clic en el nombre para ver su perfil">Proveedores que lo adjudican</SectionTitle>
                    <Card>
                      <RankList rows={topProveedores} hrefOf={(k) => `/historico/proveedor/${encodeURIComponent(k)}`} emptyLabel="Sin proveedores" />
                    </Card>
                  </section>
                </div>

                {multiEnt && (
                  <section>
                    <SectionTitle hint="Cuánto gastó cada entidad en el bien · clic para ver la entidad">Monto por entidad</SectionTitle>
                    <Card>
                      <RankList rows={rankMonto} hrefOf={(k) => `/historico/entidad/${encodeURIComponent(k)}`} emptyLabel="Sin entidades" />
                    </Card>
                  </section>
                )}

                {/* Procesos */}
                <section>
                  <SectionTitle hint="Cada proceso/licitación donde aparece el bien · clic en el CUCE para ver el proceso">
                    Procesos ({fmtNum(procesos.length)})
                  </SectionTitle>
                  <div className="bg-white rounded-xl border border-gray-200 overflow-hidden overflow-x-auto">
                    <table className="w-full text-sm min-w-[680px]">
                      <thead>
                        <tr className="border-b border-gray-100 bg-gray-50 text-xs text-gray-500">
                          <th className="text-left px-4 py-3 font-medium">Fecha</th>
                          {multiEnt && <th className="text-left px-4 py-3 font-medium">Entidad</th>}
                          <th className="text-left px-4 py-3 font-medium">Modalidad</th>
                          <th className="text-right px-4 py-3 font-medium">Cantidad</th>
                          <th className="text-right px-4 py-3 font-medium">Monto</th>
                          <th className="text-left px-4 py-3 font-medium">Proceso</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-50">
                        {procesos.map((p) => (
                          <tr key={p.cuce} className="hover:bg-gray-50 align-top">
                            <td className="px-4 py-3 text-xs text-gray-500 tabular-nums">{p.fecha ?? '—'}</td>
                            {multiEnt && (
                              <td className="px-4 py-3 text-xs text-gray-700 max-w-[220px] whitespace-normal break-words leading-tight">{p.entidad}</td>
                            )}
                            <td className="px-4 py-3 text-xs text-gray-600">{p.modalidad ?? '—'}</td>
                            <td className="px-4 py-3 text-xs text-gray-600 text-right tabular-nums">{fmtNum(p.cant)}</td>
                            <td className="px-4 py-3 text-xs font-semibold text-emerald-700 text-right tabular-nums">{fmtMonto(p.monto)}</td>
                            <td className="px-4 py-3 text-xs">
                              <Link href={`/historico/proceso/${encodeURIComponent(p.cuce)}`} className="font-mono text-[11px] text-gray-500 hover:text-blue-600 hover:underline">
                                {p.cuce}
                              </Link>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>

                {/* Detalle de compras */}
                <section>
                  <SectionTitle hint="Todas las compras del producto en el alcance">Detalle de compras</SectionTitle>
                  <div className="bg-white rounded-xl border border-gray-200 overflow-hidden overflow-x-auto">
                    <table className="w-full text-sm min-w-[760px]">
                      <thead>
                        <tr className="border-b border-gray-100 bg-gray-50 text-xs text-gray-500">
                          <th className="text-left px-4 py-3 font-medium">Entidad</th>
                          <th className="text-left px-4 py-3 font-medium">Fecha</th>
                          <th className="text-right px-4 py-3 font-medium">Cantidad</th>
                          <th className="text-right px-4 py-3 font-medium">Precio unit.</th>
                          <th className="text-right px-4 py-3 font-medium">Monto</th>
                          <th className="text-left px-4 py-3 font-medium">Proveedor</th>
                          <th className="text-left px-4 py-3 font-medium">Proceso</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-50">
                        {filas.map((f, i) => (
                          <tr key={i} className="hover:bg-gray-50 align-top">
                            <td className="px-4 py-3 text-xs text-gray-700 max-w-[260px] whitespace-normal break-words leading-tight">
                              {f.entidad}
                              {f.entidadCodigo && <span className="block text-[10px] text-gray-400 mt-0.5">{f.entidadCodigo}</span>}
                            </td>
                            <td className="px-4 py-3 text-xs text-gray-500 tabular-nums">{f.fecha ?? '—'}</td>
                            <td className="px-4 py-3 text-xs text-gray-600 text-right tabular-nums">
                              {fmtNum(f.cantidad)}{f.unidad ? ` ${f.unidad}` : ''}
                            </td>
                            <td className="px-4 py-3 text-xs text-gray-600 text-right tabular-nums">{f.precio > 0 ? fmtMonto(f.precio) : '—'}</td>
                            <td className="px-4 py-3 text-xs font-semibold text-emerald-700 text-right tabular-nums">{fmtMonto(f.monto)}</td>
                            <td className="px-4 py-3 text-xs max-w-[200px]">
                              {f.proveedorHref ? (
                                <Link href={f.proveedorHref} className="text-gray-500 hover:text-blue-600 hover:underline line-clamp-2 leading-tight">{f.proveedor}</Link>
                              ) : (
                                <span className="text-gray-500">—</span>
                              )}
                            </td>
                            <td className="px-4 py-3 text-xs">
                              <Link href={`/historico/proceso/${encodeURIComponent(f.cuce)}`} className="font-mono text-[11px] text-gray-500 hover:text-blue-600 hover:underline">
                                {f.cuce}
                              </Link>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>
              </>
            )}
          </>
        )}
      </div>
    </main>
  )
}

function Empty() {
  return <div className="h-[200px] flex items-center justify-center text-sm text-gray-400">Sin datos</div>
}
