'use client'

import { useRouter, useSearchParams, usePathname } from 'next/navigation'
import { useCallback, useTransition } from 'react'

interface Props {
  entidades: { codigo: string; nombre: string }[]
  anios: number[]
  entidad: string
  desde: string
  hasta: string
}

export default function HistFilters({ entidades, anios, entidad, desde, hasta }: Props) {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const [pending, startTransition] = useTransition()

  const update = useCallback(
    (updates: Record<string, string>) => {
      const params = new URLSearchParams(searchParams.toString())
      Object.entries(updates).forEach(([k, v]) => {
        if (v) params.set(k, v)
        else params.delete(k)
      })
      startTransition(() => router.replace(`${pathname}${params.toString() ? `?${params}` : ''}`))
    },
    [router, pathname, searchParams],
  )

  const hayFiltros = entidad !== '' || desde !== '' || hasta !== ''

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4">
      <div className="flex flex-wrap gap-3 items-center">
        <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Filtrar por</span>

        <select
          value={entidad}
          onChange={(e) => update({ entidad: e.target.value })}
          className="text-sm border border-gray-200 rounded-lg px-3 py-2 bg-white max-w-xs flex-1
                     focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">Todas las entidades</option>
          {entidades.map((e) => (
            <option key={e.codigo} value={e.codigo}>{e.nombre}</option>
          ))}
        </select>

        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-400">Años</span>
          <select
            value={desde}
            onChange={(e) => update({ desde: e.target.value })}
            className="text-sm border border-gray-200 rounded-lg px-2 py-2 bg-white
                       focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">desde</option>
            {anios.map((a) => (
              <option key={a} value={String(a)}>{a}</option>
            ))}
          </select>
          <span className="text-gray-300">–</span>
          <select
            value={hasta}
            onChange={(e) => update({ hasta: e.target.value })}
            className="text-sm border border-gray-200 rounded-lg px-2 py-2 bg-white
                       focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">hasta</option>
            {anios.map((a) => (
              <option key={a} value={String(a)}>{a}</option>
            ))}
          </select>
        </div>

        {pending && <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />}

        {hayFiltros && (
          <button
            onClick={() => update({ entidad: '', desde: '', hasta: '' })}
            className="text-xs text-gray-400 hover:text-gray-600 underline"
          >
            Limpiar
          </button>
        )}
      </div>
    </div>
  )
}
