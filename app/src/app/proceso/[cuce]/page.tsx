import Link from 'next/link'
import { notFound } from 'next/navigation'
import { getProcesoBySlug } from '@/lib/queries'
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
  const proceso = await getProcesoBySlug(cuce_decoded)

  if (!proceso) notFound()

  const sicoesUrl = `https://sicoes.gob.bo/portal/contrataciones/ficha/fichaProceso.php?cp=${cuce_decoded}`

  return (
    <main className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-5">
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

      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8 space-y-6">
        {/* Breadcrumb */}
        <nav className="text-sm text-gray-500">
          <Link href="/" className="hover:text-blue-600">Procesos</Link>
          <span className="mx-2">/</span>
          <span className="font-mono text-gray-700">{cuce_decoded}</span>
        </nav>

        {/* Card principal */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-6">
          {/* Título + estado */}
          <div className="flex items-start justify-between gap-4">
            <h2 className="text-xl font-semibold text-gray-900 leading-snug">{proceso.objeto}</h2>
            <EstadoBadge estado={proceso.estado} />
          </div>

          {/* Grid de campos */}
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
            <Campo label="Año CUCE" value={proceso.cuce_anio ? `${2000 + proceso.cuce_anio}` : '—'} />
          </dl>

          {/* Enlace a SICOES */}
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

        {/* Placeholder ítems */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Ítems del proceso</h3>
          <p className="text-sm text-gray-400">
            Disponible cuando se procesen los formularios PDF de este proceso.
          </p>
        </div>
      </div>
    </main>
  )
}
