export const dynamic = 'force-dynamic'

import Link from 'next/link'
import SiteHeader from '@/components/SiteHeader'
import { getDemandaDemo, fmtMonto, fmtNum } from '@/lib/demanda'

export default async function DemandaDetallePage({ params }: { params: Promise<{ clave: string }> }) {
  const { clave } = await params
  const decoded = decodeURIComponent(clave)
  const { productos } = await getDemandaDemo()
  const p = productos.find((x) => x.clave === decoded)

  if (!p) {
    return (
      <main className="min-h-screen bg-gray-50">
        <SiteHeader maxWidth="max-w-5xl" />
        <div className="max-w-5xl mx-auto px-4 py-10">
          <Link href="/historico/demanda-demo" className="text-sm text-blue-700">← Demanda (demo)</Link>
          <p className="mt-4 text-gray-600">No se encontró el producto <code>{decoded}</code>.</p>
        </div>
      </main>
    )
  }

  // evolución por año (adjudicado)
  const porAnio = new Map<number, { adj: number; cant: number }>()
  for (const e of p.items) {
    const y = e.fecha ? Number(e.fecha.slice(0, 4)) : null
    if (!y) continue
    const r = porAnio.get(y) ?? { adj: 0, cant: 0 }
    r.adj += e.montoAdjudicado ?? 0
    r.cant += e.cantidad ?? 0
    porAnio.set(y, r)
  }
  const anios = Array.from(porAnio.entries()).sort((a, b) => a[0] - b[0])
  const maxAdj = Math.max(1, ...anios.map(([, v]) => v.adj))

  // por entidad
  const porEntidad = new Map<string, { adj: number; cant: number; n: number }>()
  for (const e of p.items) {
    const k = e.entidad ?? '—'
    const r = porEntidad.get(k) ?? { adj: 0, cant: 0, n: 0 }
    r.adj += e.montoAdjudicado ?? 0
    r.cant += e.cantidad ?? 0
    r.n += 1
    porEntidad.set(k, r)
  }
  const entidades = Array.from(porEntidad.entries()).sort((a, b) => b[1].adj - a[1].adj)

  const items = [...p.items].sort((a, b) => (b.montoAdjudicado ?? 0) - (a.montoAdjudicado ?? 0))

  return (
    <main className="min-h-screen bg-gray-50">
      <SiteHeader maxWidth="max-w-5xl" />
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-6">
        <Link href="/historico/demanda-demo" className="text-sm text-blue-700">← Demanda (demo)</Link>

        <div>
          <h2 className="text-xl font-bold text-gray-900">{p.label}</h2>
          <p className="text-xs text-gray-500 mt-1">
            Familia <strong>{p.familia}</strong> · subfamilia <strong>{p.subfamilia}</strong> · nivel{' '}
            <strong>{p.nivel}</strong> · motor <code>{p.motor}</code> · clave <code>{p.clave}</code>
          </p>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          <Stat t="Entidades" v={String(p.entidades.size)} />
          <Stat t="Procesos" v={String(p.cuces.size)} />
          <Stat t="Cantidad" v={fmtNum(p.cantidad)} />
          <Stat t="Adjudicado" v={fmtMonto(p.montoAdjudicado)} acento />
          <Stat t="Ejecutado" v={fmtMonto(p.montoEjecutado)} />
        </div>

        {anios.length > 0 && (
          <section>
            <h3 className="text-sm font-semibold text-gray-700 mb-2">Evolución por año (adjudicado)</h3>
            <div className="rounded-xl border border-gray-200 bg-white p-4 space-y-2">
              {anios.map(([y, v]) => (
                <div key={y} className="flex items-center gap-3">
                  <span className="w-12 text-xs text-gray-500 tabular-nums">{y}</span>
                  <div className="flex-1 bg-gray-100 rounded h-5 overflow-hidden">
                    <div className="h-full bg-blue-500/80" style={{ width: `${(v.adj / maxAdj) * 100}%` }} />
                  </div>
                  <span className="w-24 text-right text-xs tabular-nums text-gray-600">{fmtMonto(v.adj)}</span>
                  <span className="w-16 text-right text-[11px] tabular-nums text-gray-400">{fmtNum(v.cant)} u</span>
                </div>
              ))}
            </div>
          </section>
        )}

        <section>
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Entidades que lo demandan</h3>
          <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[11px] uppercase tracking-wide text-gray-400 border-b border-gray-100">
                  <th className="px-3 py-2 font-medium">Entidad</th>
                  <th className="px-3 py-2 font-medium text-right">Ítems</th>
                  <th className="px-3 py-2 font-medium text-right">Cantidad</th>
                  <th className="px-3 py-2 font-medium text-right">Adjudicado</th>
                </tr>
              </thead>
              <tbody>
                {entidades.map(([e, v]) => (
                  <tr key={e} className="border-b border-gray-50">
                    <td className="px-3 py-2 text-gray-700">
                      <Link href={`/historico/entidad/${encodeURIComponent(e)}`} className="hover:text-blue-700">{e}</Link>
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums text-gray-500">{v.n}</td>
                    <td className="px-3 py-2 text-right tabular-nums text-gray-500">{fmtNum(v.cant)}</td>
                    <td className="px-3 py-2 text-right tabular-nums font-medium text-gray-800">{fmtMonto(v.adj)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section>
          <h3 className="text-sm font-semibold text-gray-700 mb-2">
            Ítems de origen ({items.length}) — trazabilidad hasta el proceso
          </h3>
          <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[11px] uppercase tracking-wide text-gray-400 border-b border-gray-100">
                  <th className="px-3 py-2 font-medium">Proceso (CUCE)</th>
                  <th className="px-3 py-2 font-medium">Descripción original</th>
                  <th className="px-3 py-2 font-medium">Fuentes</th>
                  <th className="px-3 py-2 font-medium text-right">Cant.</th>
                  <th className="px-3 py-2 font-medium text-right">Ref.</th>
                  <th className="px-3 py-2 font-medium text-right">Adj.</th>
                </tr>
              </thead>
              <tbody>
                {items.slice(0, 200).map((e, i) => (
                  <tr key={`${e.cuce}-${e.nroItem}-${i}`} className="border-b border-gray-50 align-top">
                    <td className="px-3 py-2 whitespace-nowrap">
                      <Link href={`/historico/proceso/${encodeURIComponent(e.cuce)}`} className="text-blue-700 text-xs">{e.cuce}</Link>
                      {e.incierto && <span className="ml-1 text-amber-500 text-[11px]" title="correspondencia incierta">⚠</span>}
                    </td>
                    <td className="px-3 py-2 text-xs text-gray-600 max-w-md">{e.descripcion}</td>
                    <td className="px-3 py-2 text-[11px] text-gray-400">{e.fuentes.join(', ')}</td>
                    <td className="px-3 py-2 text-right tabular-nums text-gray-500 text-xs">{e.cantidad != null ? fmtNum(e.cantidad) : '—'}</td>
                    <td className="px-3 py-2 text-right tabular-nums text-gray-500 text-xs">{e.montoReferencial != null ? fmtMonto(e.montoReferencial) : '—'}</td>
                    <td className="px-3 py-2 text-right tabular-nums text-gray-700 text-xs">{e.montoAdjudicado != null ? fmtMonto(e.montoAdjudicado) : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {items.length > 200 && <p className="text-[11px] text-gray-400 mt-2">Mostrando 200 de {items.length}.</p>}
        </section>
      </div>
    </main>
  )
}

function Stat({ t, v, acento }: { t: string; v: string; acento?: boolean }) {
  return (
    <div className={`rounded-xl border p-3 ${acento ? 'border-indigo-200 bg-indigo-50/50' : 'border-gray-200 bg-white'}`}>
      <div className="text-[11px] uppercase tracking-wide text-gray-400">{t}</div>
      <div className={`text-base font-bold mt-0.5 ${acento ? 'text-indigo-700' : 'text-gray-900'}`}>{v}</div>
    </div>
  )
}
