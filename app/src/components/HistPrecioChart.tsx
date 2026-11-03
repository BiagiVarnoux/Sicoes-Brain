'use client'

import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  Cell,
} from 'recharts'

type Point = { fecha: string; precio: number; entidad: string; cantidad: number }

// Paleta categórica validada (orden fijo, nunca ciclada). El 9º+ cae en "Otras".
const CAT = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#4a3aa7', '#e34948']
const OTRAS = '#9ca3af'
const MAX_SERIES = 8

function fmtY(v: number): string {
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`
  if (v >= 1_000) return `${(v / 1_000).toFixed(0)}K`
  return String(v)
}

const fmtX = (v: number) => new Date(v).toLocaleDateString('es-BO', { month: 'short', year: '2-digit' })

/**
 * Dispersión de precio unitario adjudicado de un producto a lo largo del tiempo,
 * coloreado por entidad (≥2 entidades → leyenda). Muestra qué tan distinto paga
 * cada entidad por el mismo bien.
 */
export default function HistPrecioChart({ data }: { data: Point[] }) {
  // Entidades por volumen de puntos, tope 8 + "Otras".
  const counts = new Map<string, number>()
  for (const d of data) counts.set(d.entidad, (counts.get(d.entidad) ?? 0) + 1)
  const orden = Array.from(counts.entries())
    .sort((a, b) => b[1] - a[1])
    .map(([e]) => e)
  const principales = orden.slice(0, MAX_SERIES)
  const colorDe = (e: string) => {
    const i = principales.indexOf(e)
    return i === -1 ? OTRAS : CAT[i]
  }
  const grupo = (e: string) => (principales.includes(e) ? e : 'Otras')

  const chartData = data.map((d) => ({
    x: new Date(d.fecha + 'T00:00:00').getTime(),
    y: d.precio,
    entidad: d.entidad,
    grupo: grupo(d.entidad),
    cantidad: d.cantidad,
    fecha: d.fecha,
  }))

  const series = [...principales]
  if (orden.length > MAX_SERIES) series.push('Otras')

  return (
    <ResponsiveContainer width="100%" height={300}>
      <ScatterChart margin={{ left: 8, right: 16, top: 8, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis
          dataKey="x"
          type="number"
          domain={['auto', 'auto']}
          tickFormatter={fmtX}
          tick={{ fontSize: 11, fill: '#6b7280' }}
          axisLine={false}
          tickLine={false}
          scale="time"
          name="fecha"
        />
        <YAxis
          dataKey="y"
          tickFormatter={fmtY}
          tick={{ fontSize: 11, fill: '#6b7280' }}
          axisLine={false}
          tickLine={false}
          name="precio"
        />
        <ZAxis range={[60, 60]} />
        <Tooltip
          cursor={{ strokeDasharray: '3 3' }}
          content={({ active, payload }) => {
            if (!active || !payload?.length) return null
            const d = payload[0].payload
            return (
              <div className="bg-white border border-gray-200 rounded-lg p-3 shadow text-xs space-y-1">
                <div className="font-medium text-gray-900">
                  Bs. {Number(d.y).toLocaleString('es-BO', { minimumFractionDigits: 2 })}
                </div>
                <div className="text-gray-500">{d.entidad}</div>
                <div className="text-gray-400">
                  {Number(d.cantidad).toLocaleString('es-BO')} u. ·{' '}
                  {new Date(d.x).toLocaleDateString('es-BO', { day: '2-digit', month: 'long', year: 'numeric' })}
                </div>
              </div>
            )
          }}
        />
        <Legend wrapperStyle={{ fontSize: 11 }} iconType="circle" iconSize={8} />
        {series.map((s) => {
          const pts = chartData.filter((d) => d.grupo === s)
          const fill = s === 'Otras' ? OTRAS : colorDe(s)
          const label = s.length > 28 ? s.slice(0, 26) + '…' : s
          return (
            <Scatter key={s} name={label} data={pts} fill={fill} isAnimationActive={false}>
              {pts.map((_, i) => (
                <Cell key={i} fill={fill} fillOpacity={0.8} />
              ))}
            </Scatter>
          )
        })}
      </ScatterChart>
    </ResponsiveContainer>
  )
}
