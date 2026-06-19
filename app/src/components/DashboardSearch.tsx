'use client'

import { useRouter, useSearchParams, usePathname } from 'next/navigation'
import { useCallback, useTransition } from 'react'

interface Props {
  entidades: { codigo: string; nombre: string }[]
  anios: number[]
  q: string
  entidad: string
  anio: string
  orderBy: string
}

export default function DashboardSearch({ entidades, anios, q, entidad, anio, orderBy }: Props) {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const [pending, startTransition] = useTransition()

  const update = useCallback(
    (updates: Record<string, string>) => {
      const params = new URLSearchParams(searchParams.toString())
      // reset page when filters change
      params.delete('page')
      Object.entries(updates).forEach(([k, v]) => {
        if (v) params.set(k, v)
        else params.delete(k)
      })
      startTransition(() => router.replace(`${pathname}?${params.toString()}`))
    },
    [router, pathname, searchParams]
  )

  const hayFiltrosGlobales = entidad !== '' || anio !== ''

  return (
    <div className="space-y-3">
      {/* Filtros globales — afectan KPIs, gráficos y tabla */}
      <div className="bg-white border border-gray-200 rounded-xl p-4">
        <div className="flex flex-wrap gap-3 items-center">
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Filtrar por</span>

          {/* Año */}
          <select
            value={anio}
            onChange={(e) => update({ anio: e.target.value })}
            className="text-sm border border-gray-200 rounded-lg px-3 py-2 bg-white
                       focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Todos los años</option>
            {anios.map((a) => (
              <option key={a} value={String(a)}>{a}</option>
            ))}
          </select>

          {/* Entidad */}
          <select
            value={entidad}
            onChange={(e) => update({ entidad: e.target.value })}
            className="text-sm border border-gray-200 rounded-lg px-3 py-2 bg-white
                       focus:outline-none focus:ring-2 focus:ring-blue-500 max-w-xs flex-1"
          >
            <option value="">Todas las entidades</option>
            {entidades.map((e) => (
              <option key={e.codigo} value={e.codigo}>{e.nombre}</option>
            ))}
          </select>

          {pending && (
            <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          )}

          {hayFiltrosGlobales && (
            <button
              onClick={() => update({ entidad: '', anio: '' })}
              className="text-xs text-gray-400 hover:text-gray-600 underline"
            >
              Limpiar filtros
            </button>
          )}
        </div>
      </div>

      {/* Filtro de búsqueda de producto — solo afecta la tabla de bienes */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none"
            fill="none" stroke="currentColor" viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            defaultValue={q}
            placeholder="Buscar producto…"
            onChange={(e) => update({ q: e.target.value })}
            className="w-full pl-9 pr-3 py-2 text-sm text-gray-900 placeholder:text-gray-400
                       border border-gray-200 rounded-lg bg-white
                       focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        <div className="flex rounded-lg border border-gray-200 overflow-hidden bg-white text-sm">
          {([
            { key: 'monto',   label: 'Por monto' },
            { key: 'veces',   label: 'Por procesos' },
            { key: 'compras', label: 'Por compras' },
          ] as const).map(({ key, label }, i) => (
            <button
              key={key}
              onClick={() => update({ order: key })}
              className={`px-3 py-2 font-medium transition-colors ${i > 0 ? 'border-l border-gray-200' : ''} ${
                orderBy === key || (!orderBy && key === 'monto') ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-50'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
