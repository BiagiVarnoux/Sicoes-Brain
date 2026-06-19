export const dynamic = 'force-dynamic'

import Link from 'next/link'
import { Suspense } from 'react'

import {
  getKPIsFiltrados,
  getTopEntidadesPorMonto,
  getTopProductos,
  getTopProveedores,
  getEntidades,
  getAniosDisponibles,
} from '@/lib/queries'
import BarChart from '@/components/BarChart'
import DashboardSearch from '@/components/DashboardSearch'
import SiteHeader from '@/components/SiteHeader'

function formatMonto(n: number) {
  if (n >= 1_000_000_000) return `Bs. ${(n / 1_000_000_000).toFixed(1)}B`
  if (n >= 1_000_000) return `Bs. ${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `Bs. ${(n / 1_000).toFixed(0)}K`
  return `Bs. ${n.toLocaleString('es-BO')}`
}

function StatCard({ label, value, sub, color }: {
  label: string; value: string; sub?: string; color: string
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className={`w-8 h-1 rounded-full mb-3 ${color}`} />
      <div className="text-2xl font-bold text-gray-900 tabular-nums">{value}</div>
      <div className="text-sm font-medium text-gray-600 mt-1">{label}</div>
      {sub && <div className="text-xs text-gray-400 mt-0.5">{sub}</div>}
    </div>
  )
}

const PAGE_SIZE = 10

type Props = {
  searchParams: Promise<{ q?: string; entidad?: string; anio?: string; order?: string; page?: string }>
}

export default async function DashboardPage({ searchParams }: Props) {
  const sp      = await searchParams
  const q       = sp.q       ?? ''
  const entidad = sp.entidad ?? ''
  const anio    = sp.anio    ?? ''
  const orderBy = (sp.order === 'veces' ? 'veces' : 'monto') as 'monto' | 'veces'
  const page    = Math.max(1, parseInt(sp.page ?? '1', 10))

  const anioNum = anio ? parseInt(anio, 10) : null

  const [kpis, topEntidades, topProductos, topProveedores, entidades, aniosDisponibles] = await Promise.all([
    getKPIsFiltrados(anioNum, entidad),
    getTopEntidadesPorMonto(10, anioNum),
    getTopProductos({ limit: 50, q, entidad, orderBy, anio: anioNum }),
    getTopProveedores(10, anioNum, entidad),
    getEntidades(),
    getAniosDisponibles(),
  ])

  const entidadData = topEntidades.map((r) => ({
    label: r.entidad.length > 32 ? r.entidad.slice(0, 30) + '…' : r.entidad,
    value: r.monto,
  }))

  const hayFiltros  = q !== '' || entidad !== '' || anio !== ''
  const totalItems  = topProductos.length
  const totalPages  = Math.max(1, Math.ceil(totalItems / PAGE_SIZE))
  const currentPage = Math.min(page, totalPages)
  const pageItems   = topProductos.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE)

  // Panel de análisis — computado de los resultados filtrados
  const filtroMonto     = topProductos.reduce((s, p) => s + (p.monto_total ?? 0), 0)
  const filtroVeces     = topProductos.reduce((s, p) => s + (p.veces ?? 0), 0)
  const filtroPrecioMin = topProductos.length
    ? Math.min(...topProductos.map((p) => p.precio_min ?? Infinity).filter((v) => isFinite(v)))
    : null
  const filtroPrecioMax = topProductos.length
    ? Math.max(...topProductos.map((p) => p.precio_max ?? 0))
    : null

  const claseMap = new Map<string, { monto: number; veces: number }>()
  topProductos.forEach((p) => {
    const k = p.clase || 'Sin categoría'
    const prev = claseMap.get(k) ?? { monto: 0, veces: 0 }
    claseMap.set(k, { monto: prev.monto + (p.monto_total ?? 0), veces: prev.veces + (p.veces ?? 0) })
  })
  const claseData = Array.from(claseMap.entries())
    .map(([label, v]) => ({ label, ...v }))
    .sort((a, b) => b.monto - a.monto)
    .slice(0, 5)

  function pageUrl(p: number) {
    const params = new URLSearchParams()
    if (q) params.set('q', q)
    if (entidad) params.set('entidad', entidad)
    if (anio) params.set('anio', anio)
    if (orderBy !== 'monto') params.set('order', orderBy)
    if (p > 1) params.set('page', String(p))
    const qs = params.toString()
    return `/dashboard${qs ? `?${qs}` : ''}`
  }

  const entidadNombre = entidades.find((e) => e.codigo === entidad)?.nombre
  const subtitulo = [
    entidadNombre ?? (entidad ? entidad : null),
    anio || null,
  ].filter(Boolean).join(' · ')

  return (
    <main className="min-h-screen bg-gray-50">
      <SiteHeader maxWidth="max-w-6xl" />

      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 space-y-6">

        {/* Título + filtros globales */}
        <div>
          <h2 className="text-xl font-bold text-gray-900">
            Dashboard
            {subtitulo && (
              <span className="ml-2 text-base font-normal text-blue-600">{subtitulo}</span>
            )}
          </h2>
          <p className="text-xs text-gray-400 mt-0.5">
            Seleccioná un año o entidad para ver los datos filtrados en todos los paneles
          </p>
        </div>

        <Suspense>
          <DashboardSearch
            entidades={entidades.map(e => ({ codigo: e.codigo, nombre: e.nombre }))}
            anios={aniosDisponibles.map(a => a.anio)}
            q={q}
            entidad={entidad}
            anio={anio}
            orderBy={orderBy}
          />
        </Suspense>

        {/* KPI Cards — reflejan los filtros activos */}
        <section className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <StatCard label="Procesos" value={kpis.totalProcesos.toLocaleString('es-BO')}
            sub={subtitulo || 'todas las entidades'} color="bg-blue-500" />
          <StatCard label="Monto adjudicado" value={formatMonto(kpis.montoTotal)}
            sub="contratos cerrados" color="bg-emerald-500" />
          <StatCard label="Ítems adjudicados" value={kpis.totalItems.toLocaleString('es-BO')}
            sub="bienes y servicios" color="bg-violet-500" />
          <StatCard label="Proveedores" value={kpis.totalProveedores.toLocaleString('es-BO')}
            sub="empresas y personas" color="bg-amber-500" />
        </section>

        {/* Bienes — tabla con búsqueda de texto */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">Bienes contratados</h2>
              <p className="text-xs text-gray-400 mt-0.5">
                {hayFiltros
                  ? `${topProductos.length} resultado${topProductos.length !== 1 ? 's' : ''}`
                  : `Top ${topProductos.length} por monto adjudicado`}
              </p>
            </div>
          </div>

          {/* Panel de análisis — cuando hay búsqueda de texto */}
          {q !== '' && topProductos.length > 0 && (
            <div className="mb-4 bg-blue-50 border border-blue-100 rounded-xl p-4 space-y-3">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-blue-700 uppercase tracking-wide">Resumen</span>
                <span className="text-xs text-blue-400">"{q}" · {topProductos.length} producto{topProductos.length !== 1 ? 's' : ''}</span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="bg-white rounded-lg border border-blue-100 p-3">
                  <div className="text-xs text-gray-500 mb-0.5">Monto total</div>
                  <div className="text-sm font-bold text-emerald-700 tabular-nums">{formatMonto(filtroMonto)}</div>
                </div>
                <div className="bg-white rounded-lg border border-blue-100 p-3">
                  <div className="text-xs text-gray-500 mb-0.5">Total contratos</div>
                  <div className="text-sm font-bold text-gray-800 tabular-nums">{filtroVeces.toLocaleString('es-BO')}</div>
                </div>
                <div className="bg-white rounded-lg border border-blue-100 p-3">
                  <div className="text-xs text-gray-500 mb-0.5">Precio mínimo</div>
                  <div className="text-sm font-bold text-gray-800 tabular-nums">
                    {filtroPrecioMin != null && isFinite(filtroPrecioMin) ? formatMonto(filtroPrecioMin) : '—'}
                  </div>
                </div>
                <div className="bg-white rounded-lg border border-blue-100 p-3">
                  <div className="text-xs text-gray-500 mb-0.5">Precio máximo</div>
                  <div className="text-sm font-bold text-gray-800 tabular-nums">
                    {filtroPrecioMax ? formatMonto(filtroPrecioMax) : '—'}
                  </div>
                </div>
              </div>
              {claseData.length > 1 && (
                <div>
                  <div className="text-xs text-blue-600 font-medium mb-2">Por categoría</div>
                  <div className="space-y-1.5">
                    {claseData.map((c) => {
                      const pct = filtroMonto > 0 ? Math.round((c.monto / filtroMonto) * 100) : 0
                      return (
                        <div key={c.label} className="flex items-center gap-2">
                          <div className="text-xs text-gray-600 w-40 truncate flex-shrink-0">{c.label}</div>
                          <div className="flex-1 bg-blue-100 rounded-full h-1.5 overflow-hidden">
                            <div className="h-full bg-blue-500 rounded-full" style={{ width: `${pct}%` }} />
                          </div>
                          <div className="text-xs text-gray-500 tabular-nums w-8 text-right">{pct}%</div>
                          <div className="text-xs text-emerald-700 font-medium tabular-nums w-20 text-right">{formatMonto(c.monto)}</div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}
            </div>
          )}

          {topProductos.length === 0 ? (
            <div className="bg-white rounded-xl border border-gray-200 p-10 text-center">
              <p className="text-gray-400 text-sm">
                {hayFiltros
                  ? 'Ningún producto coincide con los filtros.'
                  : 'No hay ítems procesados aún. Corré el scraper para poblar esta sección.'}
              </p>
              {hayFiltros && (
                <Link href="/dashboard" className="text-xs text-blue-600 hover:underline mt-2 inline-block">
                  Limpiar filtros
                </Link>
              )}
            </div>
          ) : (
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-100 bg-gray-50">
                    <th className="text-left px-4 py-3 font-medium text-gray-500 text-xs">Descripción</th>
                    <th className="text-left px-4 py-3 font-medium text-gray-500 text-xs hidden sm:table-cell">Categoría</th>
                    <th className="text-right px-4 py-3 font-medium text-gray-500 text-xs">
                      {orderBy === 'veces' ? '↓ Frecuencia' : 'Frecuencia'}
                    </th>
                    <th className="text-right px-4 py-3 font-medium text-gray-500 text-xs">
                      {orderBy === 'monto' || !orderBy ? '↓ Monto total' : 'Monto total'}
                    </th>
                    <th className="text-right px-4 py-3 font-medium text-gray-500 text-xs hidden md:table-cell">Precio unitario</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {pageItems.map((p, i) => (
                    <tr key={i} className="hover:bg-gray-50 group">
                      <td className="px-4 py-3 max-w-xs">
                        <Link
                          href={`/producto/${encodeURIComponent(p.descripcion)}`}
                          className="text-xs font-medium text-gray-800 group-hover:text-blue-600
                                     line-clamp-2 leading-tight transition-colors"
                        >
                          {p.descripcion}
                        </Link>
                      </td>
                      <td className="px-4 py-3 hidden sm:table-cell">
                        <span className="text-xs text-gray-400">{p.clase}</span>
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums">
                        <span className="text-xs font-semibold text-gray-700">{p.veces}</span>
                        <span className="text-xs text-gray-400 ml-1">{p.veces === 1 ? 'vez' : 'veces'}</span>
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums">
                        <span className="text-xs font-semibold text-emerald-700">{formatMonto(p.monto_total)}</span>
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums hidden md:table-cell">
                        {p.precio_min === p.precio_max ? (
                          <span className="text-xs text-gray-500">{formatMonto(p.precio_min)}</span>
                        ) : (
                          <span className="text-xs text-gray-500">
                            {formatMonto(p.precio_min)} – {formatMonto(p.precio_max)}
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {totalPages > 1 && (
                <div className="px-4 py-3 border-t border-gray-100 flex items-center justify-between">
                  <span className="text-xs text-gray-400">
                    {(currentPage - 1) * PAGE_SIZE + 1}–{Math.min(currentPage * PAGE_SIZE, totalItems)} de {totalItems}
                  </span>
                  <div className="flex items-center gap-1">
                    {currentPage > 1 && (
                      <Link href={pageUrl(currentPage - 1)}
                        className="px-3 py-1.5 text-xs border border-gray-200 rounded-lg text-gray-600 hover:bg-gray-50">
                        ← Anterior
                      </Link>
                    )}
                    {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
                      <Link key={p} href={pageUrl(p)}
                        className={`px-3 py-1.5 text-xs rounded-lg transition-colors ${
                          p === currentPage ? 'bg-blue-600 text-white' : 'border border-gray-200 text-gray-600 hover:bg-gray-50'
                        }`}>
                        {p}
                      </Link>
                    ))}
                    {currentPage < totalPages && (
                      <Link href={pageUrl(currentPage + 1)}
                        className="px-3 py-1.5 text-xs border border-gray-200 rounded-lg text-gray-600 hover:bg-gray-50">
                        Siguiente →
                      </Link>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </section>

        {/* Segunda fila: Top entidades + Top proveedores — ambos filtrados */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <section>
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
              Por entidad {anio && <span className="font-normal text-gray-400">· {anio}</span>}
            </h2>
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h3 className="text-sm font-semibold text-gray-700 mb-4">Top 10 por monto adjudicado</h3>
              <BarChart data={entidadData} layout="vertical" color="#2563eb" format="monto" />
            </div>
          </section>

          <section>
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
              Proveedores {subtitulo && <span className="font-normal text-gray-400">· {subtitulo}</span>}
            </h2>
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-100">
                <h3 className="text-sm font-semibold text-gray-700">Top 10 por monto adjudicado</h3>
              </div>
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-100">
                    <th className="text-left px-4 py-2.5 text-xs font-medium text-gray-500">Proveedor</th>
                    <th className="text-right px-4 py-2.5 text-xs font-medium text-gray-500">Contratos</th>
                    <th className="text-right px-4 py-2.5 text-xs font-medium text-gray-500">Monto</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {topProveedores.map((p, i) => (
                    <tr key={i} className="hover:bg-gray-50 group">
                      <td className="px-4 py-2.5 text-xs font-medium text-gray-800 max-w-[200px]">
                        <Link href={`/proveedor/${p.proveedor_id}`}
                          className="line-clamp-1 hover:text-blue-600 transition-colors">
                          {p.proveedor}
                        </Link>
                      </td>
                      <td className="px-4 py-2.5 text-xs text-gray-500 text-right tabular-nums">{p.contratos}</td>
                      <td className="px-4 py-2.5 text-xs font-semibold text-emerald-700 text-right tabular-nums">
                        {formatMonto(p.monto_total)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </div>

      </div>
    </main>
  )
}
