'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabase'
import type { ConvocatoriaRadar } from '@/lib/types'

function diasRestantes(fecha: string | null): number | null {
  if (!fecha) return null
  const hoy = new Date()
  hoy.setHours(0, 0, 0, 0)
  const f = new Date(fecha + 'T00:00:00')
  return Math.round((f.getTime() - hoy.getTime()) / 86_400_000)
}

export default function RadarTable({ rows }: { rows: ConvocatoriaRadar[] }) {
  const router = useRouter()
  const [busy, setBusy] = useState<string | null>(null)

  async function actualizar(cuce: string, campo: 'visto' | 'descartado', valor: boolean) {
    setBusy(cuce + campo)
    const { error } = await supabase
      .from('convocatorias_radar')
      .update({ [campo]: valor, actualizado_en: new Date().toISOString() })
      .eq('cuce', cuce)
    setBusy(null)
    if (error) {
      alert('No se pudo actualizar: ' + error.message)
      return
    }
    router.refresh()
  }

  if (rows.length === 0) {
    return (
      <div className="text-center py-16 text-gray-400 text-sm">
        No hay convocatorias para esta vista. Corré el radar para traer nuevas.
      </div>
    )
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs uppercase tracking-wide text-gray-500 border-b border-gray-200">
            <th className="px-4 py-3">Objeto</th>
            <th className="px-3 py-3">Entidad</th>
            <th className="px-3 py-3 whitespace-nowrap">Modalidad</th>
            <th className="px-3 py-3 whitespace-nowrap">Cierra</th>
            <th className="px-3 py-3">Filtros</th>
            <th className="px-3 py-3">DBC</th>
            <th className="px-3 py-3"></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {rows.map((r) => {
            const dias = diasRestantes(r.fecha_presentacion)
            const urgente = dias !== null && dias <= 3
            return (
              <tr key={r.cuce} className={`align-top ${r.visto ? 'bg-gray-50/60' : ''}`}>
                <td className="px-4 py-3 max-w-md">
                  <div className="font-medium text-gray-900 leading-snug">{r.objeto}</div>
                  <div className="text-xs text-gray-400 mt-0.5 font-mono">{r.cuce}</div>
                </td>
                <td className="px-3 py-3 text-gray-600 max-w-[180px]">{r.entidad}</td>
                <td className="px-3 py-3 whitespace-nowrap">
                  <span className="inline-flex px-2 py-0.5 rounded bg-gray-100 text-gray-700 text-xs font-medium">
                    {r.modalidad}
                  </span>
                </td>
                <td className="px-3 py-3 whitespace-nowrap">
                  <div className="text-gray-900">{r.fecha_presentacion ?? '—'}</div>
                  {dias !== null && (
                    <div className={`text-xs font-medium ${urgente ? 'text-red-600' : 'text-gray-400'}`}>
                      {dias === 0 ? 'hoy' : dias < 0 ? 'cerrada' : `en ${dias} día${dias === 1 ? '' : 's'}`}
                    </div>
                  )}
                </td>
                <td className="px-3 py-3">
                  <div className="flex flex-col gap-1">
                    {r.match_dicc && (
                      <span
                        className="inline-flex items-center px-2 py-0.5 rounded bg-blue-50 text-blue-700 text-xs font-medium"
                        title={(r.match_dicc_terminos ?? []).join(', ')}
                      >
                        📖 Diccionario
                      </span>
                    )}
                    {r.match_ia && (
                      <span
                        className="inline-flex items-center px-2 py-0.5 rounded bg-violet-50 text-violet-700 text-xs font-medium"
                        title={r.match_ia_razon ?? ''}
                      >
                        🤖 IA
                      </span>
                    )}
                  </div>
                </td>
                <td className="px-3 py-3 text-xs max-w-[200px]">
                  {(r.dbc_archivos ?? []).length > 0 ? (
                    <div className="flex flex-col gap-1">
                      {(r.dbc_archivos ?? []).map((a, i) => (
                        <a
                          key={i}
                          href={a.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800 hover:underline truncate"
                          title={a.nombre}
                        >
                          ⬇ {a.nombre}
                        </a>
                      ))}
                    </div>
                  ) : (
                    <span className="text-gray-400">{(r.archivos ?? []).length} arch.</span>
                  )}
                </td>
                <td className="px-3 py-3 whitespace-nowrap">
                  <div className="flex flex-col gap-1.5">
                    <button
                      onClick={() => actualizar(r.cuce, 'visto', !r.visto)}
                      disabled={busy === r.cuce + 'visto'}
                      className="text-xs px-2 py-1 rounded border border-gray-200 text-gray-600
                                 hover:bg-gray-50 disabled:opacity-50"
                    >
                      {r.visto ? '◻ No visto' : '✓ Visto'}
                    </button>
                    <button
                      onClick={() => actualizar(r.cuce, 'descartado', !r.descartado)}
                      disabled={busy === r.cuce + 'descartado'}
                      className="text-xs px-2 py-1 rounded border border-gray-200 text-gray-500
                                 hover:bg-red-50 hover:text-red-600 disabled:opacity-50"
                    >
                      {r.descartado ? '↩ Recuperar' : '✕ Descartar'}
                    </button>
                  </div>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
