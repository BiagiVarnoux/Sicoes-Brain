export const dynamic = 'force-dynamic'

import Link from 'next/link'
import { Suspense } from 'react'

import {
  getKPIsGlobales,
  getTopEntidadesPorMonto,
  getTopProductos,
  getTopProveedores,
  getEntidades,
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

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <h3 className="text-sm font-semibold text-gray-700 mb-4">{title}</h3>
      {children}
    </div>
  )
}

const PAGE_SIZE = 10

type Props = {
  searchParams: Promise<{ q?: string; entidad?: string; order?: string; page?: string }>
}

export default async function DashboardPage({ searchParams }: Props) {
  const sp = await searchParams
  const q        = sp.q        ?? ''
  const entidad  = sp.entidad  ?? ''
  const orderBy  = (sp.order === 'veces' ? 'veces' : 'monto') as 'monto' | 'veces'
  const page     = Math.max(1, parseInt(sp.page ?? '1', 10))

  const [kpis, topEntidades, topProductos, topProveedores, entidades] = await Promise.all([
    getKPIsGlobales(),
    getTopEntidadesPorMonto(10),
    getTopProductos({ limit: 50, q, entidad, orderBy }),
    getTopProveedores(10),
    getEntidades(),
  ])

  const entidadData = topEntidades.map((r) => ({
    label: r.entidad.length > 32 ? r.entidad.slice(0, 30) + '…' : r.entidad,
    value: r.monto,
  }))

  const hayFiltros   = q !== '' || entidad !== ''
  const totalItems   = topProductos.length
  const totalPages   = Math.max(1, Math.ceil(totalItems / PAGE_SIZE))
  const currentPage  = Math.min(page, totalPages)
  const pageItems    = topProductos.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE)

  function pageUrl(p: number) {
    const params = new URLSearchParams()
    if (q) params.set('q', q)
    if (entidad) params.set('entidad', entidad)
    if (orderBy !== 'monto') params.set('order', orderBy)
    if (p > 1) params.set('page', String(p))
    const qs = params.toString()
    return `/dashboard${qs ? `?${qs}` : ''}`
  }

  return (
    <main className="min-h-screen bg-gray-50">
      <SiteHeader maxWidth="max-w-6xl" />

      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8 space-y-8">

        {/* KPI Cards */}
        <section className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <StatCard label="Procesos indexados" value={kpis.totalProcesos.toLocaleString('es-BO')}
            sub="de todas las entidades" color="bg-blue-500" />
          <StatCard label="Monto adjudicado" value={formatMonto(kpis.montoTotal)}
            sub="en contratos cerrados" color="bg-emerald-500" />
          <StatCard label="Ítems únicos" value={kpis.totalItems.toLocaleString('es-BO')}
            sub="bienes y servicios" color="bg-violet-500" />
          <StatCard label="Proveedores únicos" value={kpis.totalProveedores.toLocaleString('es-BO')}
            sub="empresas y personas" color="bg-amber-500" />
        </section>

        {/* Bienes — sección principal */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <div>
              <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
                Bienes contratados
              </h2>
              <p className="text-xs text-gray-400 mt-0.5">
                {hayFiltros
                  ? `${topProductos.length} resultado${topProductos.length !== 1 ? 's' : ''}`
                  : `Top ${topProductos.length} por monto adjudicado`}
              </p>
            </div>
          </div>

          {/* Barra de búsqueda y filtros */}
          <div className="mb-4">
            <Suspense>
              <DashboardSearch
                entidades={entidades.map(e => ({ codigo: e.codigo, nombre: e.nombre }))}
                q={q}
                entidad={entidad}
                orderBy={orderBy}
              />
            </Suspense>
          </div>
          <div className="mb-1 flex items-center justify-between">
            <p className="text-xs text-gray-400">
              {hayFiltros
                ? `${totalItems} resultado${totalItems !== 1 ? 's' : ''}`
                : `${totalItems} productos`}
              {totalPages > 1 && ` · página ${currentPage} de ${totalPages}`}
            </p>
          </div>

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
                        <span className="text-xs text-gray-400 ml-1">
                          {p.veces === 1 ? 'vez' : 'veces'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right tabular-nums">
                        <span className="text-xs font-semibold text-emerald-700">
                          {formatMonto(p.monto_total)}
                        </span>
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

              {/* Paginación */}
              {totalPages > 1 && (
                <div className="px-4 py-3 border-t border-gray-100 flex items-center justify-between">
                  <span className="text-xs text-gray-400">
                    {(currentPage - 1) * PAGE_SIZE + 1}–{Math.min(currentPage * PAGE_SIZE, totalItems)} de {totalItems}
                  </span>
                  <div className="flex items-center gap-1">
                    {currentPage > 1 && (
                      <Link
                        href={pageUrl(currentPage - 1)}
                        className="px-3 py-1.5 text-xs border border-gray-200 rounded-lg
                                   text-gray-600 hover:bg-gray-50 transition-colors"
                      >
                        ← Anterior
                      </Link>
                    )}
                    {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
                      <Link
                        key={p}
                        href={pageUrl(p)}
                        className={`px-3 py-1.5 text-xs rounded-lg transition-colors ${
                          p === currentPage
                            ? 'bg-blue-600 text-white'
                            : 'border border-gray-200 text-gray-600 hover:bg-gray-50'
                        }`}
                      >
                        {p}
                      </Link>
                    ))}
                    {currentPage < totalPages && (
                      <Link
                        href={pageUrl(currentPage + 1)}
                        className="px-3 py-1.5 text-xs border border-gray-200 rounded-lg
                                   text-gray-600 hover:bg-gray-50 transition-colors"
                      >
                        Siguiente →
                      </Link>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </section>

        {/* Segunda fila: Top entidades + Top proveedores */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <section>
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Por entidad</h2>
            <ChartCard title="Top 10 entidades por monto adjudicado">
              <BarChart data={entidadData} layout="vertical" color="#2563eb" format="monto" />
            </ChartCard>
          </section>

          <section>
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Proveedores</h2>
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
                        <Link
                          href={`/proveedor/${p.proveedor_id}`}
                          className="line-clamp-1 hover:text-blue-600 transition-colors"
                        >
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
