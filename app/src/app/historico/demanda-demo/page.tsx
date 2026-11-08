export const dynamic = 'force-dynamic'

import Link from 'next/link'
import SiteHeader from '@/components/SiteHeader'
import HistTabs from '@/components/HistTabs'
import { getDemandaDemo, fmtMonto, fmtNum, type Confianza } from '@/lib/demanda'

const CONF_STYLE: Record<Confianza, { label: string; cls: string }> = {
  confirmado: { label: 'Confirmado', cls: 'bg-green-100 text-green-800 border-green-200' },
  alta: { label: 'Provisional · alta', cls: 'bg-blue-50 text-blue-700 border-blue-200' },
  media: { label: 'Provisional · media', cls: 'bg-amber-50 text-amber-700 border-amber-200' },
  baja: { label: 'Provisional · baja', cls: 'bg-gray-100 text-gray-600 border-gray-200' },
  sin_grupo: { label: 'Sin grupo', cls: 'bg-gray-100 text-gray-500 border-gray-200' },
}

function Badge({ c }: { c: Confianza }) {
  const s = CONF_STYLE[c] ?? CONF_STYLE.baja
  return <span className={`inline-block px-2 py-0.5 text-[11px] font-medium rounded-full border ${s.cls}`}>{s.label}</span>
}

export default async function DemandaDemoPage() {
  const { productos, filasCrudas, itemsEconomicos, crudoRef, colapRef, dobleConteo, meta } = await getDemandaDemo()

  const totAdj = productos.reduce((s, p) => s + p.montoAdjudicado, 0)
  const familias = new Map<string, { n: number; monto: number }>()
  for (const p of productos) {
    const f = familias.get(p.familia) ?? { n: 0, monto: 0 }
    f.n += 1
    f.monto += p.montoAdjudicado
    familias.set(p.familia, f)
  }
  const topFamilias = Array.from(familias.entries()).sort((a, b) => b[1].monto - a[1].monto)

  return (
    <main className="min-h-screen bg-gray-50">
      <SiteHeader maxWidth="max-w-6xl" />
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-6">
        <HistTabs />

        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <h2 className="text-xl font-bold text-gray-900">Demanda por producto canónico</h2>
            <span className="px-2 py-0.5 text-[11px] font-semibold rounded-full bg-indigo-100 text-indigo-700 border border-indigo-200">
              DEMO · solo lectura
            </span>
          </div>
          <p className="text-xs text-gray-500 mt-1 max-w-3xl">
            Cuánto demanda el Estado del mismo producto, sumando entidades, con las fases económicas
            separadas (referencial / adjudicado / ejecutado) y <strong>sin doble conteo</strong>. Los
            grupos son <strong>provisionales</strong>, generados fuera de producción por el motor de
            consumibles de impresión y el pipeline de atributos; no son asignaciones confirmadas por un
            humano ni están escritas en la base.
          </p>
          <p className="text-[11px] text-gray-400 mt-1">
            Fuente provisional: <code>{meta.version}</code> · commit <code>{meta.commit}</code> · generado{' '}
            {meta.generado_en} · {meta.cobertura.descripciones_asignadas} de{' '}
            {meta.cobertura.descripciones_unicas_total} descripciones únicas asignadas.
          </p>
        </div>

        {/* Banner de control anti doble-conteo */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <Card titulo="Filas hist_items" valor={fmtNum(filasCrudas)} sub="registros crudos" />
          <Card titulo="Ítems económicos" valor={fmtNum(itemsEconomicos)} sub="tras colapsar por (cuce, ítem)" />
          <Card titulo="Referencial colapsado" valor={fmtMonto(colapRef)} sub={`crudo ${fmtMonto(crudoRef)}`} />
          <Card
            titulo="Doble conteo evitado"
            valor={fmtMonto(dobleConteo)}
            sub={`${((dobleConteo / colapRef) * 100).toFixed(1)}% del referencial`}
            acento
          />
        </div>

        {/* Familias */}
        <section>
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Familias (por monto adjudicado)</h3>
          <div className="flex flex-wrap gap-2">
            {topFamilias.map(([fam, v]) => (
              <span key={fam} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white border border-gray-200 text-xs">
                <span className="font-medium text-gray-800">{fam}</span>
                <span className="text-gray-400">·</span>
                <span className="text-gray-500">{v.n} productos</span>
                <span className="text-gray-400">·</span>
                <span className="font-semibold text-gray-700">{fmtMonto(v.monto)}</span>
              </span>
            ))}
          </div>
        </section>

        {/* Tabla de productos */}
        <section>
          <div className="flex items-baseline justify-between mb-2">
            <h3 className="text-sm font-semibold text-gray-700">
              Productos canónicos ({productos.length})
            </h3>
            <span className="text-[11px] text-gray-400">{fmtMonto(totAdj)} adjudicado agrupado</span>
          </div>
          <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-[11px] uppercase tracking-wide text-gray-400 border-b border-gray-100">
                  <th className="px-3 py-2.5 font-medium">Producto</th>
                  <th className="px-3 py-2.5 font-medium">Estado</th>
                  <th className="px-3 py-2.5 font-medium text-right">Entid.</th>
                  <th className="px-3 py-2.5 font-medium text-right">Proc.</th>
                  <th className="px-3 py-2.5 font-medium text-right">Cant.</th>
                  <th className="px-3 py-2.5 font-medium text-right">Referencial</th>
                  <th className="px-3 py-2.5 font-medium text-right">Adjudicado</th>
                  <th className="px-3 py-2.5 font-medium text-right">Ejecutado</th>
                </tr>
              </thead>
              <tbody>
                {productos.slice(0, 120).map((p) => (
                  <tr key={p.clave} className="border-b border-gray-50 hover:bg-gray-50/60">
                    <td className="px-3 py-2.5">
                      <Link
                        href={`/historico/demanda-demo/${encodeURIComponent(p.clave)}`}
                        className="font-medium text-gray-800 hover:text-blue-700"
                      >
                        {p.label}
                      </Link>
                      <div className="text-[11px] text-gray-400">
                        {p.familia}
                        {p.inciertos > 0 && <span className="text-amber-500"> · {p.inciertos} ítem(s) inciertos</span>}
                      </div>
                    </td>
                    <td className="px-3 py-2.5"><Badge c={p.confianza} /></td>
                    <td className="px-3 py-2.5 text-right tabular-nums text-gray-600">{p.entidades.size}</td>
                    <td className="px-3 py-2.5 text-right tabular-nums text-gray-600">{p.cuces.size}</td>
                    <td className="px-3 py-2.5 text-right tabular-nums text-gray-600">{fmtNum(p.cantidad)}</td>
                    <td className="px-3 py-2.5 text-right tabular-nums text-gray-500">{p.montoReferencial ? fmtMonto(p.montoReferencial) : '—'}</td>
                    <td className="px-3 py-2.5 text-right tabular-nums font-semibold text-gray-800">{p.montoAdjudicado ? fmtMonto(p.montoAdjudicado) : '—'}</td>
                    <td className="px-3 py-2.5 text-right tabular-nums text-gray-500">{p.montoEjecutado ? fmtMonto(p.montoEjecutado) : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {productos.length > 120 && (
            <p className="text-[11px] text-gray-400 mt-2">Mostrando los 120 de mayor monto adjudicado.</p>
          )}
        </section>

        <p className="text-[11px] text-gray-400 border-t border-gray-100 pt-3">
          <strong>Nota metodológica.</strong> nivel=producto afirma intercambiabilidad (mismo código de
          consumible o mismos atributos técnicos); subfamilia/familia agregan por tipo sin afirmar que
          sean el mismo ítem. El referencial se toma del formulario de requerimiento (FORM100/110) cuando
          existe; adjudicado y ejecutado vienen de FORM200/220/500. Las tres fases nunca se suman entre sí.
        </p>
      </div>
    </main>
  )
}

function Card({ titulo, valor, sub, acento }: { titulo: string; valor: string; sub?: string; acento?: boolean }) {
  return (
    <div className={`rounded-xl border p-3 ${acento ? 'border-indigo-200 bg-indigo-50/50' : 'border-gray-200 bg-white'}`}>
      <div className="text-[11px] uppercase tracking-wide text-gray-400">{titulo}</div>
      <div className={`text-lg font-bold mt-0.5 ${acento ? 'text-indigo-700' : 'text-gray-900'}`}>{valor}</div>
      {sub && <div className="text-[11px] text-gray-400 mt-0.5">{sub}</div>}
    </div>
  )
}
