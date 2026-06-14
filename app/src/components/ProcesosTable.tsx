import Link from 'next/link'
import { type Proceso } from '@/lib/types'
import EstadoBadge from './EstadoBadge'

type Props = {
  procesos: Proceso[]
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
    month: 'short',
    year: 'numeric',
  })
}

export default function ProcesosTable({ procesos }: Props) {
  if (procesos.length === 0) {
    return (
      <div className="text-center py-16 text-gray-400">
        <p className="text-lg">No se encontraron procesos</p>
        <p className="text-sm mt-1">Intentá con otros filtros</p>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-gray-200">
      <table className="min-w-full divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left font-semibold text-gray-600 w-36">CUCE</th>
            <th className="px-4 py-3 text-left font-semibold text-gray-600">Objeto</th>
            <th className="px-4 py-3 text-left font-semibold text-gray-600 w-48">Entidad</th>
            <th className="px-4 py-3 text-left font-semibold text-gray-600 w-16">Mod.</th>
            <th className="px-4 py-3 text-left font-semibold text-gray-600 w-32">Estado</th>
            <th className="px-4 py-3 text-left font-semibold text-gray-600 w-28">Publicación</th>
            <th className="px-4 py-3 text-right font-semibold text-gray-600 w-32">Monto Ref.</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white">
          {procesos.map((p) => (
            <tr key={p.cuce} className="hover:bg-blue-50 transition-colors">
              <td className="px-4 py-3 font-mono text-xs text-gray-500 whitespace-nowrap">
                <Link href={`/proceso/${encodeURIComponent(p.cuce)}`} className="hover:text-blue-600 hover:underline">
                  {p.cuce}
                </Link>
              </td>
              <td className="px-4 py-3 text-gray-800 max-w-xs">
                <Link
                  href={`/proceso/${encodeURIComponent(p.cuce)}`}
                  className="line-clamp-2 hover:text-blue-600"
                >
                  {p.objeto}
                </Link>
              </td>
              <td className="px-4 py-3 text-gray-600 text-xs line-clamp-2">{p.entidad_nombre ?? '—'}</td>
              <td className="px-4 py-3">
                <span className="font-mono text-xs bg-gray-100 text-gray-700 px-1.5 py-0.5 rounded">
                  {p.modalidad ?? '—'}
                </span>
              </td>
              <td className="px-4 py-3">
                <EstadoBadge estado={p.estado} />
              </td>
              <td className="px-4 py-3 text-gray-500 text-xs whitespace-nowrap">
                {formatFecha(p.fecha_publicacion)}
              </td>
              <td className="px-4 py-3 text-right text-gray-700 font-medium whitespace-nowrap">
                {formatMonto(p.monto_referencial)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
