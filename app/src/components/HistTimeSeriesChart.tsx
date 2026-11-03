'use client'

import {
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts'

type Point = { label: string; valor: number; proyeccion?: boolean }

const BLUE = '#2a78d6'

function fmt(v: number): string {
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`
  if (v >= 1_000) return `${(v / 1_000).toFixed(0)}K`
  return String(Math.round(v))
}

/**
 * Serie temporal de monto (un solo eje, una sola serie → sin leyenda).
 * El tramo de proyección se dibuja punteado y en tono atenuado.
 */
export default function HistTimeSeriesChart({
  data,
  firstProjIndex,
  unidad = 'Bs.',
}: {
  data: Point[]
  firstProjIndex?: number | null
  unidad?: string
}) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <ComposedChart data={data} margin={{ left: 0, right: 12, top: 8, bottom: 4 }}>
        <defs>
          <linearGradient id="histArea" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={BLUE} stopOpacity={0.18} />
            <stop offset="100%" stopColor={BLUE} stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
        <XAxis
          dataKey="label"
          tick={{ fontSize: 10, fill: '#9ca3af' }}
          axisLine={false}
          tickLine={false}
          interval="preserveStartEnd"
          minTickGap={16}
        />
        <YAxis
          tickFormatter={fmt}
          tick={{ fontSize: 10, fill: '#9ca3af' }}
          axisLine={false}
          tickLine={false}
          width={40}
        />
        <Tooltip
          content={({ active, payload }) => {
            if (!active || !payload?.length) return null
            const d = payload[0].payload as Point
            return (
              <div className="bg-white border border-gray-200 rounded-lg p-3 shadow text-xs space-y-1">
                <div className="font-semibold text-gray-800">{d.label}</div>
                <div className="text-blue-700 font-medium">
                  {unidad} {Number(d.valor).toLocaleString('es-BO', { maximumFractionDigits: 0 })}
                </div>
                {d.proyeccion && <div className="text-gray-400">proyección</div>}
              </div>
            )
          }}
        />
        {firstProjIndex != null && firstProjIndex > 0 && data[firstProjIndex] && (
          <ReferenceLine x={data[firstProjIndex].label} stroke="#d1d5db" strokeDasharray="4 4" />
        )}
        <Area
          type="monotone"
          dataKey="valor"
          stroke={BLUE}
          strokeWidth={2}
          fill="url(#histArea)"
          dot={false}
          isAnimationActive={false}
          activeDot={{ r: 4, strokeWidth: 0 }}
        />
      </ComposedChart>
    </ResponsiveContainer>
  )
}
