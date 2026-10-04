'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabase'
import { type ConvocatoriaRadar, MOTIVOS_DESCARTE } from '@/lib/types'

function diasRestantes(fecha: string | null): number | null {
  if (!fecha) return null
  const hoy = new Date()
  hoy.setHours(0, 0, 0, 0)
  const f = new Date(fecha + 'T00:00:00')
  return Math.round((f.getTime() - hoy.getTime()) / 86_400_000)
}

function labelMotivo(code: string) {
  return MOTIVOS_DESCARTE.find((m) => m.code === code)?.label ?? code
}

export default function RadarTable({ rows }: { rows: ConvocatoriaRadar[] }) {
  const router = useRouter()
  const [busy, setBusy] = useState<string | null>(null)

  // Estado del modal de descarte
  const [descartando, setDescartando] = useState<ConvocatoriaRadar | null>(null)
  const [motivosSel, setMotivosSel] = useState<string[]>([])
  const [nota, setNota] = useState('')

  async function toggleVisto(cuce: string, visto: boolean) {
    setBusy(cuce + 'visto')
    const { error } = await supabase
      .from('convocatorias_radar')
      .update({ visto, actualizado_en: new Date().toISOString() })
      .eq('cuce', cuce)
    setBusy(null)
    if (error) return alert('No se pudo actualizar: ' + error.message)
    router.refresh()
  }

  async function recuperar(cuce: string) {
    setBusy(cuce + 'rec')
    const { error } = await supabase
      .from('convocatorias_radar')
      .update({
        descartado: false, motivo_descarte: [], nota_descarte: null,
        descartado_en: null, actualizado_en: new Date().toISOString(),
      })
      .eq('cuce', cuce)
    setBusy(null)
    if (error) return alert('No se pudo recuperar: ' + error.message)
    router.refresh()
  }

  function abrirDescarte(r: ConvocatoriaRadar) {
    setDescartando(r)
    setMotivosSel(r.motivo_descarte ?? [])
    setNota(r.nota_descarte ?? '')
  }

  async function confirmarDescarte() {
    if (!descartando) return
    if (motivosSel.length === 0) return alert('Elegí al menos un motivo.')
    const cuce = descartando.cuce
    setBusy(cuce + 'desc')
    const { error } = await supabase
      .from('convocatorias_radar')
      .update({
        descartado: true,
        motivo_descarte: motivosSel,
        nota_descarte: nota.trim() || null,
        descartado_en: new Date().toISOString(),
        actualizado_en: new Date().toISOString(),
      })
      .eq('cuce', cuce)
    setBusy(null)
    setDescartando(null)
    if (error) return alert('No se pudo descartar: ' + error.message)
    router.refresh()
  }

  if (rows.length === 0) {
    return (
      <div className="text-center py-16 text-gray-400 text-sm">
        No hay convocatorias para esta vista. Corré el radar para traer nuevas.
      </div>
    )
  }

  const entrenaSel = motivosSel.some((c) => MOTIVOS_DESCARTE.find((m) => m.code === c)?.entrena)

  return (
    <>
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
                    {r.descartado && (r.motivo_descarte ?? []).length > 0 && (
                      <div className="mt-1.5 flex flex-wrap gap-1">
                        {(r.motivo_descarte ?? []).map((m) => (
                          <span key={m} className="inline-flex px-1.5 py-0.5 rounded bg-red-50 text-red-600 text-[11px]">
                            {labelMotivo(m)}
                          </span>
                        ))}
                        {r.nota_descarte && (
                          <span className="text-[11px] text-gray-500 italic">· {r.nota_descarte}</span>
                        )}
                      </div>
                    )}
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
                        <span className="inline-flex items-center px-2 py-0.5 rounded bg-blue-50 text-blue-700 text-xs font-medium"
                          title={(r.match_dicc_terminos ?? []).join(', ')}>
                          📖 Diccionario
                        </span>
                      )}
                      {r.match_ia && (
                        <span className="inline-flex items-center px-2 py-0.5 rounded bg-violet-50 text-violet-700 text-xs font-medium"
                          title={r.match_ia_razon ?? ''}>
                          🤖 IA
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-3 py-3 text-xs max-w-[200px]">
                    {(r.dbc_archivos ?? []).length > 0 ? (
                      <div className="flex flex-col gap-1">
                        {(r.dbc_archivos ?? []).map((a, i) => (
                          <a key={i} href={a.url} target="_blank" rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800 hover:underline truncate"
                            title={a.nombre}>
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
                        onClick={() => toggleVisto(r.cuce, !r.visto)}
                        disabled={busy === r.cuce + 'visto'}
                        className="text-xs px-2 py-1 rounded border border-gray-200 text-gray-600 hover:bg-gray-50 disabled:opacity-50">
                        {r.visto ? '◻ No visto' : '✓ Visto'}
                      </button>
                      {r.descartado ? (
                        <button
                          onClick={() => recuperar(r.cuce)}
                          disabled={busy === r.cuce + 'rec'}
                          className="text-xs px-2 py-1 rounded border border-gray-200 text-gray-500 hover:bg-gray-50 disabled:opacity-50">
                          ↩ Recuperar
                        </button>
                      ) : (
                        <button
                          onClick={() => abrirDescarte(r)}
                          className="text-xs px-2 py-1 rounded border border-gray-200 text-gray-500 hover:bg-red-50 hover:text-red-600">
                          ✕ Descartar
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Modal de descarte por motivos */}
      {descartando && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
          onClick={() => setDescartando(null)}>
          <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-5" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-base font-semibold text-gray-900">Descartar convocatoria</h3>
            <p className="text-xs text-gray-500 mt-1 line-clamp-2">{descartando.objeto}</p>

            <div className="mt-4 space-y-1.5">
              <p className="text-xs font-medium text-gray-700">¿Por qué la descartás? (uno o varios)</p>
              {MOTIVOS_DESCARTE.map((m) => (
                <label key={m.code} className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={motivosSel.includes(m.code)}
                    onChange={(e) =>
                      setMotivosSel((prev) =>
                        e.target.checked ? [...prev, m.code] : prev.filter((c) => c !== m.code))
                    }
                  />
                  {m.label}
                  {m.entrena && (
                    <span className="text-[10px] px-1 py-0.5 rounded bg-amber-100 text-amber-700">entrena IA</span>
                  )}
                </label>
              ))}
            </div>

            <textarea
              value={nota}
              onChange={(e) => setNota(e.target.value)}
              placeholder={entrenaSel
                ? 'Nota (recomendado: qué producto no manejás, ej. "no hago impresoras 3D")'
                : 'Nota (opcional)'}
              className="mt-3 w-full border border-gray-200 rounded-lg p-2 text-sm h-20 resize-none"
            />

            {entrenaSel && (
              <p className="mt-2 text-[11px] text-amber-700 bg-amber-50 rounded p-2">
                Marcaste <b>Producto</b>: esto entrenará la IA/diccionario para no volver a mostrarte esa categoría.
              </p>
            )}

            <div className="mt-4 flex justify-end gap-2">
              <button onClick={() => setDescartando(null)}
                className="text-sm px-3 py-1.5 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50">
                Cancelar
              </button>
              <button onClick={confirmarDescarte}
                disabled={busy === descartando.cuce + 'desc'}
                className="text-sm px-3 py-1.5 rounded-lg bg-red-600 text-white hover:bg-red-700 disabled:opacity-50">
                Descartar
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
