'use client'

import { useRouter, usePathname } from 'next/navigation'
import { useCallback } from 'react'
import { MODALIDADES, ESTADOS, type Entidad, type SearchParams } from '@/lib/types'

type Props = {
  entidades: Entidad[]
  current: SearchParams
}

export default function SearchFilters({ entidades, current }: Props) {
  const router = useRouter()
  const pathname = usePathname()

  const update = useCallback(
    (key: string, value: string) => {
      const params = new URLSearchParams()
      if (current.q) params.set('q', current.q)
      if (current.modalidad) params.set('modalidad', current.modalidad)
      if (current.estado) params.set('estado', current.estado)
      if (current.entidad) params.set('entidad', current.entidad)
      // reset page on any filter change
      params.delete('page')

      if (value) {
        params.set(key, value)
      } else {
        params.delete(key)
      }
      router.push(`${pathname}?${params.toString()}`)
    },
    [router, pathname, current]
  )

  const handleSearch = useCallback(
    (e: React.FormEvent<HTMLFormElement>) => {
      e.preventDefault()
      const form = e.currentTarget
      const q = (form.elements.namedItem('q') as HTMLInputElement).value.trim()
      update('q', q)
    },
    [update]
  )

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5 space-y-4">
      {/* Buscador de texto */}
      <form onSubmit={handleSearch} className="flex gap-2">
        <input
          name="q"
          defaultValue={current.q ?? ''}
          placeholder="Buscar por objeto del proceso..."
          className="flex-1 border border-gray-300 rounded-lg px-4 py-2 text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          type="submit"
          className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
        >
          Buscar
        </button>
      </form>

      {/* Filtros en fila */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {/* Modalidad */}
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Modalidad</label>
          <select
            value={current.modalidad ?? ''}
            onChange={(e) => update('modalidad', e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Todas</option>
            {MODALIDADES.map((m) => (
              <option key={m.value} value={m.value}>
                {m.label}
              </option>
            ))}
          </select>
        </div>

        {/* Estado */}
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Estado</label>
          <select
            value={current.estado ?? ''}
            onChange={(e) => update('estado', e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Todos</option>
            {ESTADOS.map((e) => (
              <option key={e} value={e}>
                {e}
              </option>
            ))}
          </select>
        </div>

        {/* Entidad */}
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Entidad</label>
          <select
            value={current.entidad ?? ''}
            onChange={(e) => update('entidad', e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Todas</option>
            {entidades.map((ent) => (
              <option key={ent.codigo} value={ent.codigo}>
                {ent.nombre}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Limpiar filtros */}
      {(current.q || current.modalidad || current.estado || current.entidad) && (
        <button
          onClick={() => router.push(pathname)}
          className="text-xs text-gray-400 hover:text-gray-600 underline"
        >
          Limpiar filtros
        </button>
      )}
    </div>
  )
}
