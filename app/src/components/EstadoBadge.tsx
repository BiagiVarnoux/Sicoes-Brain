const colorMap: Record<string, string> = {
  Contratado: 'bg-green-100 text-green-800',
  Adjudicado: 'bg-blue-100 text-blue-800',
  'En curso': 'bg-yellow-100 text-yellow-800',
  Vigente: 'bg-sky-100 text-sky-800',
  Desierto: 'bg-red-100 text-red-800',
  'Desierto Parcial': 'bg-orange-100 text-orange-800',
  Cancelado: 'bg-gray-200 text-gray-600',
  'Anulado desde la convocatoria': 'bg-gray-200 text-gray-600',
  Suspendido: 'bg-purple-100 text-purple-800',
}

export default function EstadoBadge({ estado }: { estado: string | null }) {
  if (!estado) return null
  const cls = colorMap[estado] ?? 'bg-gray-100 text-gray-700'
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${cls}`}>
      {estado}
    </span>
  )
}
