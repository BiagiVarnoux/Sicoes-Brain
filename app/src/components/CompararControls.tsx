'use client'

import { useMemo, useState } from 'react'
import { useRouter, usePathname } from 'next/navigation'

import { ProvisionalBadge } from './HistUI'
import { fmtMonto } from '@/lib/historico'

type Prod = { key: string; label: string; provisional?: boolean }
type Ent = { codigo: string; nombre: string; monto: number; items: number }

function norm(s: string) {
  return s.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '')
}

/** Selector de bien (buscador) + multi-selector de entidades. El estado se
 *  guarda en la URL, así la vista se recalcula en el server y es compartible. */
export default function CompararControls({
  productos,
  selectedProducto,
  productoLabel,
  productoProvisional,
  entidades,
  selectedEntidades,
}: {
  productos: Prod[]
  selectedProducto: string | null
  productoLabel: string | null
  productoProvisional?: boolean
  entidades: Ent[]
  selectedEntidades: string[]
}) {
  const router = useRouter()
  const pathname = usePathname()

  const go = (producto: string | null, ents: string[]) => {
    const p = new URLSearchParams()
    if (producto) p.set('producto', producto)
    if (ents.length) p.set('entidades', ents.join(','))
    const qs = p.toString()
    router.push(qs ? `${pathname}?${qs}` : pathname, { scroll: false })
  }

  const [q, setQ] = useState('')
  const filtered = useMemo(() => {
    const nq = norm(q.trim())
    if (!nq) return productos.slice(0, 40)
    const terms = nq.split(/\s+/)
    return productos.filter((p) => terms.every((t) => norm(p.label).includes(t))).slice(0, 40)
  }, [q, productos])

  const sel = new Set(selectedEntidades)
  const toggleEnt = (codigo: string) => {
    const next = new Set(sel)
    if (next.has(codigo)) next.delete(codigo)
    else next.add(codigo)
    go(selectedProducto, [...next])
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 sm:p-5 space-y-4">
      {/* Paso 1 — bien */}
      <div>
        <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">1 · Bien</div>
        {selectedProducto ? (
          <div className="flex items-center gap-2 flex-wrap">
            <span className="inline-flex items-center gap-1.5 text-sm font-medium text-blue-800 bg-blue-50 border border-blue-200 rounded-lg px-3 py-1.5 max-w-full">
              <span className="line-clamp-1">{productoLabel}</span>
              {productoProvisional && <ProvisionalBadge />}
            </span>
            <button
              onClick={() => go(null, [])}
              className="text-xs text-gray-500 hover:text-gray-800 underline shrink-0"
            >
              cambiar
            </button>
          </div>
        ) : (
          <div className="relative">
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Buscar un bien por nombre…"
              autoFocus
              className="w-full pl-9 pr-3 py-2.5 text-sm border border-gray-200 rounded-lg bg-white
                         focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35M11 18a7 7 0 100-14 7 7 0 000 14z" />
            </svg>
            <div className="mt-2 max-h-72 overflow-y-auto border border-gray-100 rounded-lg divide-y divide-gray-50">
              {filtered.length === 0 ? (
                <div className="px-3 py-6 text-center text-xs text-gray-400">Sin resultados</div>
              ) : (
                filtered.map((p) => (
                  <button
                    key={p.key}
                    onClick={() => go(p.key, [])}
                    className="w-full text-left px-3 py-2 text-xs text-gray-700 hover:bg-blue-50 flex items-center gap-1.5"
                  >
                    <span className="line-clamp-1">{p.label}</span>
                    {p.provisional && <ProvisionalBadge />}
                  </button>
                ))
              )}
            </div>
          </div>
        )}
      </div>

      {/* Paso 2 — entidades */}
      {selectedProducto && (
        <div>
          <div className="flex items-center justify-between gap-2 mb-2">
            <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
              2 · Entidades <span className="font-normal text-gray-400 normal-case">· sin marcar = todas</span>
            </div>
            <div className="flex items-center gap-2 text-xs">
              <button onClick={() => go(selectedProducto, entidades.map((e) => e.codigo))} className="text-blue-600 hover:underline">
                Todas
              </button>
              <span className="text-gray-300">·</span>
              <button onClick={() => go(selectedProducto, [])} className="text-gray-500 hover:underline">
                Ninguna
              </button>
            </div>
          </div>
          {entidades.length === 0 ? (
            <div className="text-xs text-gray-400 py-4 text-center">Este bien no tiene compras registradas.</div>
          ) : (
            <div className="max-h-64 overflow-y-auto border border-gray-100 rounded-lg divide-y divide-gray-50">
              {entidades.map((e) => {
                const checked = sel.has(e.codigo)
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
      )}
    </div>
  )
}
