export const dynamic = 'force-dynamic'

import Link from 'next/link'
import { notFound } from 'next/navigation'
import { getProcesoBySlug, getItemsByProceso } from '@/lib/queries'
import EstadoBadge from '@/components/EstadoBadge'

type Props = {
  params: Promise<{ cuce: string }>
}

function formatMonto(monto: number | null) {
  if (!monto) return '—'
  return new Intl.NumberFormat('es-BO', {
    style: 'currency',
    currency: 'BOB',
    maximumFractionDigits: 0,
  }).format(monto)
}

function formatFecha(fecha: string | null) {
  if (!fecha) return '—'
  return new Date(fecha + 'T00:00:00').toLocaleDateString('es-BO', {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
  })
}

function Campo({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <dt className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</dt>
      <dd className="mt-1 text-sm text-gray-900">{value ?? '—'}</dd>
    </div>
  )
}

export default async function ProcesoPage({ params }: Props) {
  const { cuce } = await params
  const cuce_decoded = decodeURIComponent(cuce)

  const [proceso, items] = await Promise.all([
    getProcesoBySlug(cuce_decoded),
    getItemsByProceso(cuce_decoded),
  ])

  if (!proceso) notFound()

  const sicoesUrl = `https://sicoes.gob.bo/portal/contrataciones/ficha/fichaProceso.php?cp=${cuce_decoded}`

  return (
    <main className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-5">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
              <span className="text-white text-xs font-bold">S</span>
            </div>
            <div>
              <h1 className="text-lg font-semibold text-gray-900">SICOES Intelligence</h1>
              <p className="text-xs text-gray-500">Contrataciones estatales de Bolivia</p>
            </div>
          </div>
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8 space-y-6">
        {/* Breadcrumb */}
        <nav className="text-sm text-gray-500">
          <Link href="/" className="hover:text-blue-600">Procesos</Link>
          <span className="mx-2">/</span>
          <span className="font-mono text-gray-700">{cuce_decoded}</span>
        </nav>

        {/* Card principal */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-6">
          <div className="flex items-start justify-between gap-4">
            <h2 className="text-xl font-semibold text-gray-900 leading-snug">{proceso.objeto}</h2>
            <EstadoBadge estado={proceso.estado} />
          </div>

          <dl className="grid grid-cols-2 sm:grid-cols-3 gap-6">
            <Campo label="CUCE" value={<span className="font-mono text-xs">{proceso.cuce}</span>} />
            <Campo label="Modalidad" value={
              <span className="font-mono text-xs bg-gray-100 px-1.5 py-0.5 rounded">{proceso.modalidad}</span>
            } />
            <Campo label="Tipo" value={proceso.tipo_contratacion} />
            <Campo label="Entidad" value={proceso.entidad_nombre} />
            <Campo label="Publicación" value={formatFecha(proceso.fecha_publicacion)} />
            <Campo label="Presentación" value={formatFecha(proceso.fecha_presentacion)} />
            <Campo label="Monto referencial" value={
              <span className="font-medium">{formatMonto(proceso.monto_referencial)}</span>
            } />
            <Campo label="Monto adjudicado" value={
              <span className="font-medium text-green-700">{formatMonto(proceso.monto_adjudicado)}</span>
            } />
            <Campo label="Año CUCE" value={proceso.cuce_anio ?? '—'} />
          </dl>

          <div className="pt-4 border-t border-gray-100">
            <a
              href={sicoesUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-sm text-blue-600 hover:text-blue-800 font-medium"
            >
              Ver en SICOES.gob.bo
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </a>
          </div>
        </div>

        {/* Ítems */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-gray-700">
              Ítems del proceso
              {items.length > 0 && (
                <span className="ml-2 text-xs font-normal text-gray-400">({items.length} productos)</span>
              )}
            </h3>
          </div>

          {items.length === 0 ? (
            <p className="text-sm text-gray-400">
              Los ítems de este proceso aún no fueron procesados.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm divide-y divide-gray-100">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500 w-10">#</th>
                    <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500">Producto</th>
                    <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500 w-24">Unidad</th>
                    <th className="px-3 py-2 text-right text-xs font-semibold text-gray-500 w-20">Cantidad</th>
                    <th className="px-3 py-2 text-right text-xs font-semibold text-gray-500 w-28">P. Referencial</th>
                    <th className="px-3 py-2 text-right text-xs font-semibold text-gray-500 w-28">P. Adjudicado</th>
                    <th className="px-3 py-2 text-right text-xs font-semibold text-gray-500 w-28">Total</th>
                    <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500 w-32">Proveedor</th>
                    <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500 w-20">Estado</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {items.map((item: any) => (
                    <tr key={item.id} className="hover:bg-gray-50">
                      <td className="px-3 py-2 text-gray-400 text-xs">{item.nro_item}</td>
                      <td className="px-3 py-2">
                        <div className="text-gray-800 font-medium text-xs leading-tight">
                          {item.descripcion_producto}
                        </div>
                        {(item.clase_nombre ?? item.familia_nombre) && (
                          <div className="text-gray-400 text-xs mt-0.5">
                            {item.clase_nombre ?? item.familia_nombre}
                            {item.unspsc_codigo && (
                              <span className="ml-1 font-mono text-gray-300">{item.unspsc_codigo}</span>
                            )}
                          </div>
                        )}
                      </td>
                      <td className="px-3 py-2 text-gray-500 text-xs">{item.unidad_medida || '—'}</td>
                      <td className="px-3 py-2 text-right text-gray-700 text-xs">
                        {item.cantidad ? Number(item.cantidad).toLocaleString('es-BO') : '—'}
                      </td>
                      <td className="px-3 py-2 text-right text-gray-500 text-xs">
                        {formatMonto(item.precio_referencial)}
                      </td>
                      <td className="px-3 py-2 text-right text-gray-700 text-xs font-medium">
                        {formatMonto(item.precio_adjudicado)}
                      </td>
                      <td className="px-3 py-2 text-right text-gray-700 text-xs font-medium">
                        {formatMonto(item.monto_total)}
                      </td>
                      <td className="px-3 py-2 text-xs text-gray-500">
                        {item.proveedor_nombre ?? '—'}
                      </td>
                      <td className="px-3 py-2">
                        <span className={`text-xs px-1.5 py-0.5 rounded-full ${
                          item.estado_item === 'adjudicado'
                            ? 'bg-green-100 text-green-700'
                            : 'bg-red-100 text-red-700'
                        }`}>
                          {item.estado_item}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </main>
  )
}
