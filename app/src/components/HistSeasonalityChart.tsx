'use client'

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'

const MESES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
const AQUA = '#1baf7a'

function fmt(v: number): string {
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`
  if (v >= 1_000) return `${(v / 1_000).toFixed(0)}K`
  return String(Math.round(v))
}

/**
 * Estacionalidad por mes del año (una sola serie → sin leyenda).
 * El mes pico se resalta; el resto queda en el mismo tono atenuado.
 */
export default function HistSeasonalityChart({
  data,
  campo,
}: {
  data: { mes: number; monto: number; items: number; cantidad: number }[]
  campo: 'entrega' | 'publicacion'
}) {
  const chart = data.map((d) => ({ ...d, label: MESES[d.mes - 1] }))
  const max = Math.max(0, ...chart.map((d) => d.monto))

  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={chart} margin={{ left: 0, right: 8, top: 4, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
        <XAxis
          dataKey="label"
          tick={{ fontSize: 10, fill: '#9ca3af' }}
          axisLine={false}
          tickLine={false}
          interval={0}
        />
        <YAxis tickFormatter={fmt} tick={{ fontSize: 10, fill: '#9ca3af' }} axisLine={false} tickLine={false} width={40} />
        <Tooltip
          content={({ active, payload }) => {
            if (!active || !payload?.length) return null
            const d = payload[0].payload
            return (
              <div className="bg-white border border-gray-200 rounded-lg p-3 shadow text-xs space-y-1">
                <div className="font-semibold text-gray-800">{d.label}</div>
                <div className="text-emerald-700 font-medium">
                  Bs. {Number(d.monto).toLocaleString('es-BO', { maximumFractionDigits: 0 })}
                </div>
                <div className="text-gray-400">
                  {d.items} ítem{d.items !== 1 ? 's' : ''} · {Number(d.cantidad).toLocaleString('es-BO')} u.
                </div>
              </div>
            )
          }}
          cursor={{ fill: '#f9fafb' }}
        />
        <Bar dataKey="monto" radius={[3, 3, 0, 0]} maxBarSize={28} isAnimationActive={false}>
          {chart.map((d, i) => (
            <Cell key={i} fill={AQUA} opacity={max > 0 && d.monto === max ? 1 : 0.5} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
