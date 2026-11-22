'use client'

import { useRouter, usePathname, useSearchParams } from 'next/navigation'

import { fmtMonto } from '@/lib/historico'

type Ent = { codigo: string; nombre: string; monto: number; items: number }
type Anio = { anio: number; monto: number; items: number }

/** Filtros combinables de la vista de producto: multi-entidad × multi-año.
 *  El estado vive en la URL (?entidades=..&anios=..) para que la vista se
 *  recalcule en el server y sea compartible. El bien está fijado por la ruta. */
export default function ProductoControls({
  entidades,
  selectedEntidades,
  anios,
  selectedAnios,
}: {
  entidades: Ent[]
  selectedEntidades: string[]
  anios: Anio[]
  selectedAnios: number[]
}) {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()

  const go = (ents: string[], years: number[]) => {
    const p = new URLSearchParams(searchParams.toString())
    if (ents.length) p.set('entidades', ents.join(','))
    else p.delete('entidades')
    if (years.length) p.set('anios', [...years].sort((a, b) => a - b).join(','))
    else p.delete('anios')
    const qs = p.toString()
    router.push(qs ? `${pathname}?${qs}` : pathname, { scroll: false })
  }

  const entSel = new Set(selectedEntidades)
  const toggleEnt = (codigo: string) => {
    const next = new Set(entSel)
    if (next.has(codigo)) next.delete(codigo)
    else next.add(codigo)
    go([...next], selectedAnios)
  }

  const anioSel = new Set(selectedAnios)
  const toggleAnio = (anio: number) => {
    const next = new Set(anioSel)
    if (next.has(anio)) next.delete(anio)
    else next.add(anio)
    go(selectedEntidades, [...next])
  }

  const hayFiltro = selectedEntidades.length > 0 || selectedAnios.length > 0

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 sm:p-5 space-y-4">
      <div className="flex items-center justify-between gap-2">
        <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Filtros</div>
        {hayFiltro && (
          <button onClick={() => go([], [])} className="text-xs text-gray-500 hover:text-gray-800 underline">
            Limpiar
          </button>
        )}
      </div>

      {/* Años */}
      <div>
        <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
          Años <span className="font-normal text-gray-400 normal-case">· sin marcar = todos</span>
        </div>
        {anios.length === 0 ? (
          <div className="text-xs text-gray-400">Sin años registrados.</div>
        ) : (
          <div className="flex flex-wrap gap-1.5">
            {anios.map((a) => {
              const checked = anioSel.has(a.anio)
              return (
                <button
                  key={a.anio}
                  onClick={() => toggleAnio(a.anio)}
                  title={`${a.items} ít. · ${fmtMonto(a.monto)}`}
                  className={`px-2.5 py-1 rounded-lg text-xs font-medium border transition-colors tabular-nums ${
                    checked
                      ? 'bg-blue-600 border-blue-600 text-white'
                      : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'
                  }`}
                >
                  {a.anio}
                </button>
              )
            })}
          </div>
        )}
      </div>

      {/* Entidades */}
      <div>
        <div className="flex items-center justify-between gap-2 mb-2">
          <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
            Entidades <span className="font-normal text-gray-400 normal-case">· sin marcar = todas</span>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <button onClick={() => go(entidades.map((e) => e.codigo), selectedAnios)} className="text-blue-600 hover:underline">
              Todas
            </button>
            <span className="text-gray-300">·</span>
            <button onClick={() => go([], selectedAnios)} className="text-gray-500 hover:underline">
              Ninguna
            </button>
          </div>
        </div>
        {entidades.length === 0 ? (
          <div className="text-xs text-gray-400 py-4 text-center">Este bien no tiene compras registradas.</div>
        ) : (
          <div className="max-h-64 overflow-y-auto border border-gray-100 rounded-lg divide-y divide-gray-50">
            {entidades.map((e) => {
              const checked = entSel.has(e.codigo)
              return (
                <label
                  key={e.codigo}
                  className={`flex items-center gap-2.5 px-3 py-2 cursor-pointer text-xs ${checked ? 'bg-blue-50/60' : 'hover:bg-gray-50'}`}
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => toggleEnt(e.codigo)}
                    className="w-4 h-4 shrink-0 accent-blue-600"
                  />
                  <span className="flex-1 min-w-0 text-gray-700 line-clamp-1">{e.nombre}</span>
                  <span className="shrink-0 tabular-nums text-gray-400">{e.items} ít.</span>
                  <span className="shrink-0 tabular-nums font-medium text-emerald-700 w-20 text-right">{fmtMonto(e.monto)}</span>
                </label>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
