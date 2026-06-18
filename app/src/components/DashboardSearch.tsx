'use client'

import { useRouter, useSearchParams, usePathname } from 'next/navigation'
import { useCallback, useTransition } from 'react'

interface Props {
  entidades: { codigo: string; nombre: string }[]
  q: string
  entidad: string
  orderBy: string
}

export default function DashboardSearch({ entidades, q, entidad, orderBy }: Props) {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const [pending, startTransition] = useTransition()

  const update = useCallback(
    (key: string, value: string) => {
      const params = new URLSearchParams(searchParams.toString())
      if (value) params.set(key, value)
      else params.delete(key)
      startTransition(() => router.replace(`${pathname}?${params.toString()}`))
    },
    [router, pathname, searchParams]
  )

  return (
    <div className="flex flex-col sm:flex-row gap-3">
      {/* Buscador de texto */}
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
          onChange={(e) => update('q', e.target.value)}
          className="w-full pl-9 pr-3 py-2 text-sm text-gray-900 placeholder:text-gray-400
                     border border-gray-200 rounded-lg bg-white
                     focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
        {pending && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2 w-3 h-3
                          border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        )}
      </div>

      {/* Filtro entidad */}
      <select
        value={entidad}
        onChange={(e) => update('entidad', e.target.value)}
        className="text-sm border border-gray-200 rounded-lg px-3 py-2 bg-white
                   focus:outline-none focus:ring-2 focus:ring-blue-500 min-w-48"
      >
        <option value="">Todas las entidades</option>
        {entidades.map((e) => (
          <option key={e.codigo} value={e.codigo}>{e.nombre}</option>
        ))}
      </select>

      {/* Ordenar */}
      <div className="flex rounded-lg border border-gray-200 overflow-hidden bg-white text-sm">
        <button
          onClick={() => update('order', 'monto')}
          className={`px-3 py-2 font-medium transition-colors ${
            orderBy === 'monto' || !orderBy
              ? 'bg-blue-600 text-white'
              : 'text-gray-600 hover:bg-gray-50'
          }`}
        >
          Por monto
        </button>
        <button
          onClick={() => update('order', 'veces')}
          className={`px-3 py-2 font-medium transition-colors border-l border-gray-200 ${
            orderBy === 'veces'
              ? 'bg-blue-600 text-white'
              : 'text-gray-600 hover:bg-gray-50'
          }`}
        >
          Por frecuencia
        </button>
      </div>
    </div>
  )
}
