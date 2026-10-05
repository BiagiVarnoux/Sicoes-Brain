export const dynamic = 'force-dynamic'

import type { ReactNode } from 'react'
import Link from 'next/link'
import SiteHeader from '@/components/SiteHeader'
import { supabase } from '@/lib/supabase'
import type { ConvocatoriaRadar, ConvocatoriaSpecs, ErpLicitacion } from '@/lib/types'

type PageProps = { params: Promise<{ cuce: string }> }

function dias(fecha: string | null): number | null {
  if (!fecha) return null
  const hoy = new Date(); hoy.setHours(0, 0, 0, 0)
  return Math.round((new Date(fecha + 'T00:00:00').getTime() - hoy.getTime()) / 86_400_000)
}

export default async function FichaPage({ params }: PageProps) {
  const { cuce: cuceRaw } = await params
  const cuce = decodeURIComponent(cuceRaw)
  const cuce4 = cuce.split('-')[3] ?? ''

  const [{ data: cRows }, { data: sRows }, { data: eRows }] = await Promise.all([
    supabase.from('convocatorias_radar').select('*').eq('cuce', cuce).limit(1),
    supabase.from('convocatoria_specs').select('*').eq('cuce', cuce).limit(1),
    supabase.from('erp_licitaciones').select('*').eq('numero_sicoes', cuce4).limit(1),
  ])
  const c = (cRows?.[0] ?? null) as ConvocatoriaRadar | null
  const specs = (sRows?.[0] ?? null) as ConvocatoriaSpecs | null
  const erp = (eRows?.[0] ?? null) as ErpLicitacion | null

  if (!c) {
    return (
      <div className="min-h-screen bg-gray-50">
        <SiteHeader />
        <main className="max-w-4xl mx-auto px-4 sm:px-6 py-8">
          <Link href="/radar" className="text-sm text-blue-600 hover:underline">← Volver al radar</Link>
          <p className="mt-6 text-gray-500">No se encontró la convocatoria {cuce}.</p>
        </main>
      </div>
    )
  }

  const d = dias(c.fecha_presentacion)
  const Dato = ({ k, v }: { k: string; v: ReactNode }) => (
    <div><div className="text-xs text-gray-500">{k}</div><div className="text-sm text-gray-900">{v ?? '—'}</div></div>
  )

  return (
    <div className="min-h-screen bg-gray-50">
      <SiteHeader />
      <main className="max-w-4xl mx-auto px-4 sm:px-6 py-8 space-y-6">
        <Link href="/radar" className="text-sm text-blue-600 hover:underline">← Volver al radar</Link>

        <div>
          <h2 className="text-xl font-semibold text-gray-900 leading-snug">{c.objeto}</h2>
          <div className="text-xs text-gray-400 font-mono mt-1">{c.cuce}</div>
          {erp && (
            <span className={`inline-flex mt-2 px-2 py-0.5 rounded text-xs font-medium ${
              erp.ganada ? 'bg-emerald-100 text-emerald-800'
                : erp.estado === 'PERDIDA' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-800'}`}>
              🗂 Ya trabajada · {erp.estado}
            </span>
          )}
        </div>

        <section className="rounded-xl border border-gray-200 bg-white p-5 grid grid-cols-2 sm:grid-cols-3 gap-4">
          <Dato k="Entidad" v={c.entidad} />
          <Dato k="Modalidad" v={c.modalidad} />
          <Dato k="Estado" v={c.estado} />
          <Dato k="Publicación" v={c.fecha_publicacion} />
          <Dato k="Cierre (presentación)" v={
            <>{c.fecha_presentacion ?? '—'}{d !== null && (
              <span className={d <= 3 ? 'text-red-600' : 'text-gray-400'}> · {d < 0 ? 'cerrada' : `en ${d} día${d === 1 ? '' : 's'}`}</span>
            )}</>
          } />
          <Dato k="Filtros" v={
            <span className="flex gap-1">
              {c.match_dicc && <span className="px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 text-xs">📖</span>}
              {c.match_ia && <span className="px-1.5 py-0.5 rounded bg-violet-50 text-violet-700 text-xs" title={c.match_ia_razon ?? ''}>🤖</span>}
            </span>
          } />
        </section>

        {(c.dbc_archivos ?? []).length > 0 && (
          <section className="rounded-xl border border-gray-200 bg-white p-5">
            <h3 className="text-sm font-medium text-gray-700 mb-2">Documentos (DBC)</h3>
            <div className="flex flex-col gap-1">
              {(c.dbc_archivos ?? []).map((a, i) => (
                <a key={i} href={a.url} target="_blank" rel="noopener noreferrer"
                  className="text-sm text-blue-600 hover:underline">⬇ {a.nombre}</a>
              ))}
            </div>
          </section>
        )}

        <section className="rounded-xl border border-gray-200 bg-white p-5">
          <h3 className="text-sm font-medium text-gray-700 mb-3">📋 Qué pide la entidad (especificaciones del DBC)</h3>
          {(specs?.items ?? []).length === 0 ? (
            <p className="text-sm text-gray-400">Sin especificaciones extraídas (corré <code>dbc_specs.py</code>).</p>
          ) : (
            <div className="space-y-4">
              {(specs?.items ?? []).map((it, i) => (
                <div key={i}>
                  <div className="text-sm font-medium text-gray-900">
                    {it.descripcion || `Ítem ${it.item ?? i + 1}`}
                    {it.cantidad != null && (
                      <span className="text-gray-500 font-normal"> · {it.cantidad}{it.unidad ? ` ${it.unidad.toLowerCase()}` : ''}</span>
                    )}
                  </div>
                  {(it.especificaciones?.length ?? 0) > 0 && (
                    <ul className="mt-1 ml-4 list-disc text-sm text-gray-600 space-y-0.5">
                      {(it.especificaciones ?? []).map((e, j) => <li key={j}>{e}</li>)}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>

        {c.descartado && (
          <section className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            Descartada{(c.motivo_descarte ?? []).length > 0 && <> · motivos: {(c.motivo_descarte ?? []).join(', ')}</>}
            {c.nota_descarte && <> · {c.nota_descarte}</>}
          </section>
        )}
      </main>
    </div>
  )
}
