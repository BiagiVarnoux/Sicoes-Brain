'use client'

import { useMemo, useState } from 'react'
import Link from 'next/link'

import { ProvisionalBadge } from './HistUI'

export type SearchRow = {
  key: string
  href: string
  label: string
  /** Línea secundaria bajo el nombre (ej. "UNSPSC 43211503"). */
  subtitle?: string | null
  provisional?: boolean
  /** Columnas numéricas (alineadas a la derecha), en el mismo orden que colHeaders. */
  cols: string[]
  /** Texto donde se busca (se arma en el server, ya en minúsculas). */
  haystack: string
}

function norm(s: string) {
  return s.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '')
}

/** Lista/tabla con filtro instantáneo en el cliente. Sirve para productos y
 *  proveedores: encuentra también lo que no aparece en los "top". */
export default function HistSearchList({
  rows,
  colHeaders,
  placeholder,
  unitSingular,
  unitPlural,
}: {
  rows: SearchRow[]
  /** Encabezados de las columnas numéricas; la última se resalta. */
  colHeaders: string[]
  placeholder: string
  /** Sustantivos para el conteo ("producto" / "productos"). */
  unitSingular: string
  unitPlural: string
}) {
  const [q, setQ] = useState('')

  const filtered = useMemo(() => {
    const nq = norm(q.trim())
    if (!nq) return rows
    const terms = nq.split(/\s+/)
    return rows.filter((r) => terms.every((t) => r.haystack.includes(t)))
  }, [q, rows])

  const lastCol = colHeaders.length - 1

  return (
    <div className="space-y-3">
      <div className="relative">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={placeholder}
          autoFocus
          className="w-full pl-9 pr-9 py-2.5 text-sm border border-gray-200 rounded-lg bg-white
                     focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35M11 18a7 7 0 100-14 7 7 0 000 14z" />
        </svg>
        {q && (
          <button
            onClick={() => setQ('')}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 text-lg leading-none px-1"
            aria-label="Limpiar"
          >
            ×
          </button>
        )}
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden overflow-x-auto">
        <table className="w-full text-sm min-w-[520px]">
          <thead>
            <tr className="border-b border-gray-100 bg-gray-50 text-xs text-gray-500">
              <th className="text-left px-4 py-3 font-medium">Nombre</th>
              {colHeaders.map((h, i) => (
                <th key={h} className={`text-right px-4 py-3 font-medium ${i !== lastCol ? 'hidden sm:table-cell' : ''}`}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {filtered.length === 0 ? (
              <tr><td colSpan={colHeaders.length + 1} className="px-4 py-10 text-center text-gray-400 text-sm">Sin resultados para “{q}”</td></tr>
            ) : (
              filtered.slice(0, 300).map((r) => (
                <tr key={r.key} className="hover:bg-gray-50 group align-top">
                  <td className="px-4 py-3 max-w-md">
                    <Link href={r.href} className="text-xs font-medium text-gray-800 group-hover:text-blue-600 line-clamp-2 leading-tight inline-flex items-start gap-1.5">
                      <span className="line-clamp-2">{r.label}</span>
                      {r.provisional && <ProvisionalBadge />}
                    </Link>
                    {r.subtitle && <div className="text-[10px] text-gray-400 mt-0.5">{r.subtitle}</div>}
                  </td>
                  {r.cols.map((c, i) => (
                    <td
                      key={i}
                      className={`px-4 py-3 text-right tabular-nums text-xs ${
                        i === lastCol ? 'font-semibold text-emerald-700' : 'text-gray-600 hidden sm:table-cell'
                      }`}
                    >
                      {c}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <p className="text-xs text-gray-400">
        {filtered.length.toLocaleString('es-BO')} {filtered.length !== 1 ? unitPlural : unitSingular}
        {filtered.length > 300 && ' · mostrando los primeros 300, afiná la búsqueda'}
      </p>
    </div>
  )
}
