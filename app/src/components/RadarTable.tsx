'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabase'
import {
  type ConvocatoriaRadar, type ErpLicitacion, type ErpProducto,
  type ConvocatoriaSpecs, MOTIVOS_DESCARTE,
} from '@/lib/types'

function cuce4(cuce: string): string {
  const p = (cuce ?? '').split('-')
  return p[3] ?? ''
}

function norm(s: string | null): string {
  return (s ?? '').normalize('NFKD').replace(/[̀-ͯ]/g, '').toLowerCase()
}

// Tipos de producto para cruzar la convocatoria con el catálogo del ERP.
const TIPOS: { key: string; rx: RegExp }[] = [
  { key: 'ssd', rx: /\bssd\b|disco solido|estado solido|nvme/ },
  { key: 'hdd', rx: /\bhdd\b|disco duro/ },
  { key: 'ram', rx: /\bram\b|memoria ram|memorias ram|\bddr\d?\b/ },
  { key: 'backup', rx: /cinta|\blto\b|lto\d|backup/ },
  { key: 'etiqueta', rx: /etiqueta|dk-?2205|autoadhesiv/ },
  { key: 'tarjeta', rx: /tarjeta|\bpvc\b|ribbon|ymcko|zebra|zxp/ },
  { key: 'escaner', rx: /escaner|scanner/ },
  { key: 'impresion', rx: /impresora|toner|tinta|fotocopiadora/ },
  { key: 'periferico', rx: /periferic|teclado|mouse|raton|\bhub\b|adaptador|conversor|hdmi|\bvga\b|estabilizador|\bups\b|switch|regleta|altavoz|parlante|cable/ },
  { key: 'computo', rx: /computador|laptop|notebook|\bcpu\b|equipo de computacion|equipos de computacion|equipo informatico|equipos informaticos/ },
  { key: 'monitor', rx: /monitor|pantalla/ },
]

function tiposDe(texto: string): Set<string> {
  const n = norm(texto)
  const out = new Set<string>()
  for (const t of TIPOS) if (t.rx.test(n)) out.add(t.key)
  return out
}

type Referencia = { nombre: string; precio: number | null; ganada: boolean | null; estado: string | null }

function referenciasDe(
  objeto: string | null,
  productos: ErpProducto[],
  erpMap: Record<string, ErpLicitacion>,
): Referencia[] {
  const tconv = tiposDe(objeto ?? '')
  if (tconv.size === 0) return []
  const refs: Referencia[] = []
  const vistos = new Set<string>()
  for (const p of productos) {
    const tp = tiposDe(`${p.nombre ?? ''} ${p.especificacion ?? ''}`)
    let comparte = false
    for (const k of tp) if (tconv.has(k)) { comparte = true; break }
    if (!comparte) continue
    const lic = erpMap[p.numero_sicoes]
    const nombre = (p.nombre ?? '').trim() || '(sin nombre)'
    const clave = `${nombre}|${p.precio_ofertado}`
    if (vistos.has(clave)) continue
    vistos.add(clave)
    refs.push({
      nombre,
      precio: p.precio_ofertado,
      ganada: lic?.ganada ?? null,
      estado: lic?.estado ?? null,
    })
  }
  // ganadas primero, luego por precio
  refs.sort((a, b) => Number(b.ganada) - Number(a.ganada) || (a.precio ?? 0) - (b.precio ?? 0))
  return refs
}

function fmtBs(n: number | null): string {
  if (n == null) return '—'
  return 'Bs ' + n.toLocaleString('es-BO', { minimumFractionDigits: 0, maximumFractionDigits: 2 })
}

function HistorialBadge({ hist }: { hist: ErpLicitacion }) {
  const ganada = hist.ganada === true
  const perdida = hist.estado === 'PERDIDA'
  const cls = ganada
    ? 'bg-emerald-100 text-emerald-800'
    : perdida
      ? 'bg-red-100 text-red-700'
      : 'bg-amber-100 text-amber-800'
  return (
    <span
      className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[11px] font-medium ${cls}`}
      title={hist.nombre ?? ''}
    >
      🗂 Ya trabajada · {hist.estado}
    </span>
  )
}

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

export default function RadarTable(
  { rows, erpMap = {}, erpProductos = [], specsMap = {} }: {
    rows: ConvocatoriaRadar[]
    erpMap?: Record<string, ErpLicitacion>
    erpProductos?: ErpProducto[]
    specsMap?: Record<string, ConvocatoriaSpecs>
  },
) {
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
              const refs = referenciasDe(r.objeto, erpProductos, erpMap)
              const precios = refs.map((x) => x.precio).filter((x): x is number => x != null)
              const ganadas = refs.filter((x) => x.ganada === true).length
              const perdidas = refs.filter((x) => x.ganada === false).length
              const specs = (specsMap[r.cuce]?.items ?? []).filter(
                (it) => it && (it.descripcion || (it.especificaciones?.length ?? 0) > 0))
              return (
                <tr key={r.cuce} className={`align-top ${r.visto ? 'bg-gray-50/60' : ''}`}>
                  <td className="px-4 py-3 max-w-md">
                    <div className="font-medium text-gray-900 leading-snug">{r.objeto}</div>
                    <div className="text-xs text-gray-400 mt-0.5 font-mono">{r.cuce}</div>
                    {erpMap[cuce4(r.cuce)] && (
                      <div className="mt-1">
                        <HistorialBadge hist={erpMap[cuce4(r.cuce)]} />
                      </div>
                    )}
                    {refs.length > 0 && (
                      <details className="mt-1.5 group">
                        <summary className="cursor-pointer text-xs text-emerald-700 hover:underline list-none">
                          💡 Tu historial: {refs.length} oferta{refs.length === 1 ? '' : 's'} similar
                          {precios.length > 0 && (
                            <span className="text-gray-500">
                              {' · '}{fmtBs(Math.min(...precios))}–{fmtBs(Math.max(...precios))}
                            </span>
                          )}
                          {(ganadas > 0 || perdidas > 0) && (
                            <span className="text-gray-500"> · ✓{ganadas}/✗{perdidas}</span>
                          )}
                        </summary>
                        <div className="mt-1 pl-1 flex flex-col gap-0.5">
                          {refs.slice(0, 8).map((x, i) => (
                            <div key={i} className="text-[11px] text-gray-600 flex items-center gap-1.5">
                              <span className={x.ganada ? 'text-emerald-600' : x.ganada === false ? 'text-red-500' : 'text-gray-400'}>
                                {x.ganada ? '✓' : x.ganada === false ? '✗' : '•'}
                              </span>
                              <span className="font-medium text-gray-800">{fmtBs(x.precio)}</span>
                              <span className="truncate max-w-[220px]" title={x.nombre}>{x.nombre}</span>
                              <span className="text-gray-400">{x.estado}</span>
                            </div>
                          ))}
                        </div>
                      </details>
                    )}
                    {specs.length > 0 && (
                      <details className="mt-1.5">
                        <summary className="cursor-pointer text-xs text-indigo-700 hover:underline list-none">
                          📋 Qué pide la entidad: {specs.length} ítem{specs.length === 1 ? '' : 's'}
                        </summary>
                        <div className="mt-1 pl-1 flex flex-col gap-1.5">
                          {specs.map((it, i) => (
                            <div key={i} className="text-[11px]">
                              <div className="font-medium text-gray-800">
                                {it.descripcion || `Ítem ${it.item ?? i + 1}`}
                                {it.cantidad != null && (
                                  <span className="text-gray-500 font-normal">
                                    {' '}· {it.cantidad}{it.unidad ? ` ${it.unidad.toLowerCase()}` : ''}
                                  </span>
                                )}
                              </div>
                              {(it.especificaciones?.length ?? 0) > 0 && (
                                <ul className="mt-0.5 ml-3 list-disc text-gray-600 space-y-0.5">
                                  {(it.especificaciones ?? []).map((e, j) => (
                                    <li key={j}>{e}</li>
                                  ))}
                                </ul>
                              )}
                            </div>
                          ))}
                        </div>
                      </details>
                    )}
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
