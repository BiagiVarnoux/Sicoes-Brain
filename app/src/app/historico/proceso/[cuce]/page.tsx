export const dynamic = 'force-dynamic'

import Link from 'next/link'

import SiteHeader from '@/components/SiteHeader'
import HistTabs from '@/components/HistTabs'
import { StatCard, SectionTitle } from '@/components/HistUI'
import {
  getHistData,
  productoKey,
  proveedorKey,
  num,
  fmtMonto,
  fmtNum,
  type HistItem,
} from '@/lib/historico'

const valItem = (it: HistItem) => num(it.monto_total) || num(it.precio_adjudicado) * num(it.cantidad)
const precioUnit = (it: HistItem) => num(it.precio_adjudicado) || (num(it.cantidad) ? valItem(it) / num(it.cantidad) : 0)

type Props = { params: Promise<{ cuce: string }> }

export default async function ProcesoHistoricoPage({ params }: Props) {
  const { cuce: raw } = await params
  const cuce = decodeURIComponent(raw)

  const data = await getHistData()
  const proc = data.procesos.find((p) => p.cuce === cuce) ?? null
  const items = data.items.filter((it) => it.cuce === cuce)

  const entidadCodigo = proc?.entidad_codigo ?? items[0]?.entidad_codigo ?? ''
  const entidadNombre = (entidadCodigo && data.entidadNombre.get(entidadCodigo)) || proc?.entidad_nombre || entidadCodigo || '—'

  const montoAdj = items.reduce((s, it) => s + valItem(it), 0)
  const montoEjec = items.reduce((s, it) => s + num(it.monto_ejecutado), 0)
  const montoRef = items.reduce((s, it) => s + num(it.precio_referencial) * num(it.cantidad), 0)

  const notFound = !proc && items.length === 0

  const fechas: { label: string; value: string | null }[] = [
    { label: 'Publicación', value: proc?.fecha_publicacion ?? null },
    { label: 'Firma de contrato', value: proc?.fecha_firma_contrato ?? null },
    { label: 'Entrega (FORM500)', value: proc?.fecha_entrega ?? null },
  ]

  return (
    <main className="min-h-screen bg-gray-50">
      <SiteHeader maxWidth="max-w-6xl" />
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 sm:py-8 space-y-6">
        <HistTabs />
        <div>
          <Link href="/historico" className="text-xs text-blue-600 hover:underline">← Histórico</Link>
          <h2 className="text-xl font-bold text-gray-900 mt-1">{proc?.objeto?.trim() || 'Proceso de contratación'}</h2>
          <p className="text-xs text-gray-400 mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5">
            <span className="font-mono text-gray-500">{cuce}</span>
            {proc?.modalidad && <span>· {proc.modalidad}</span>}
            {proc?.cuce_anio && <span>· {proc.cuce_anio}</span>}
            {proc?.tiene_dbc && (
              <span className="inline-flex items-center gap-1 text-[10px] font-medium text-indigo-700 bg-indigo-50 border border-indigo-200 rounded-full px-2 py-0.5">
                DBC
              </span>
            )}
          </p>
          {entidadCodigo && (
            <p className="text-sm mt-2">
              <Link href={`/historico/entidad/${encodeURIComponent(entidadCodigo)}`} className="text-gray-700 hover:text-blue-600 hover:underline">
                {entidadNombre}
              </Link>
            </p>
          )}
        </div>

        {notFound ? (
          <div className="bg-white rounded-xl border border-gray-200 p-10 text-center text-sm text-gray-400">
            No hay datos para este proceso.
          </div>
        ) : (
          <>
            <section className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <StatCard label="Ítems" value={fmtNum(items.length)} sub="líneas" color="bg-violet-500" />
              <StatCard label="Referencial" value={montoRef > 0 ? fmtMonto(montoRef) : '—'} sub="presupuestado" color="bg-gray-400" />
              <StatCard label="Adjudicado" value={fmtMonto(montoAdj)} color="bg-emerald-500" />
              <StatCard label="Ejecutado" value={fmtMonto(montoEjec)} sub={montoAdj > 0 ? `${Math.round((montoEjec / montoAdj) * 100)}% del adj.` : undefined} color="bg-teal-500" />
            </section>

            <section className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {fechas.map((f) => (
                <div key={f.label} className="bg-white rounded-xl border border-gray-200 p-4">
                  <div className="text-xs text-gray-400">{f.label}</div>
                  <div className="text-sm font-medium text-gray-800 tabular-nums mt-0.5">{f.value ?? '—'}</div>
                </div>
              ))}
            </section>

            <section>
              <SectionTitle hint="Cada línea adjudicada del proceso · clic en el producto o el proveedor">Ítems adjudicados</SectionTitle>
              <div className="bg-white rounded-xl border border-gray-200 overflow-hidden overflow-x-auto">
                <table className="w-full text-sm min-w-[720px]">
                  <thead>
                    <tr className="border-b border-gray-100 bg-gray-50 text-xs text-gray-500">
                      <th className="text-left px-4 py-3 font-medium w-8">#</th>
                      <th className="text-left px-4 py-3 font-medium">Producto</th>
                      <th className="text-right px-4 py-3 font-medium">Cantidad</th>
                      <th className="text-right px-4 py-3 font-medium">Precio unit.</th>
                      <th className="text-right px-4 py-3 font-medium">Monto</th>
                      <th className="text-left px-4 py-3 font-medium">Proveedor</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {items.map((it, i) => {
                      const provKey = proveedorKey(it.proveedor)
                      return (
                        <tr key={it.id ?? i} className="hover:bg-gray-50 align-top">
                          <td className="px-4 py-3 text-xs text-gray-400 tabular-nums">{it.nro_item ?? i + 1}</td>
                          <td className="px-4 py-3 text-xs max-w-[320px]">
                            <Link href={`/historico/producto/${encodeURIComponent(productoKey(it))}`} className="text-gray-700 hover:text-blue-600 hover:underline line-clamp-2 leading-tight">
                              {(it.descripcion ?? '').trim() || '—'}
                            </Link>
                            {it.unspsc_codigo && <div className="text-[10px] text-gray-400 mt-0.5">UNSPSC {it.unspsc_codigo}</div>}
                          </td>
                          <td className="px-4 py-3 text-xs text-gray-600 text-right tabular-nums">
                            {fmtNum(num(it.cantidad))}{it.unidad_medida ? ` ${it.unidad_medida}` : ''}
                          </td>
                          <td className="px-4 py-3 text-xs text-gray-600 text-right tabular-nums">{precioUnit(it) > 0 ? fmtMonto(precioUnit(it)) : '—'}</td>
                          <td className="px-4 py-3 text-xs font-semibold text-emerald-700 text-right tabular-nums">{fmtMonto(valItem(it))}</td>
                          <td className="px-4 py-3 text-xs max-w-[220px]">
                            {it.proveedor && provKey ? (
                              <Link href={`/historico/proveedor/${encodeURIComponent(provKey)}`} className="text-gray-500 hover:text-blue-600 hover:underline line-clamp-2 leading-tight">{it.proveedor}</Link>
                            ) : (
                              <span className="text-gray-500">—</span>
                            )}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        )}
      </div>
    </main>
  )
}
