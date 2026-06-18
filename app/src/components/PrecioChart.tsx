'use client'

import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'

type Point = {
  fecha: string
  precio: number
  proveedor: string
  entidad: string
}

const COLORS = [
  '#2563eb', '#7c3aed', '#059669', '#d97706', '#dc2626',
  '#0891b2', '#7c3aed', '#65a30d', '#ea580c', '#db2777',
]

export default function PrecioChart({ data }: { data: Point[] }) {
  // Asignar color por proveedor
  const proveedores = Array.from(new Set(data.map((d) => d.proveedor)))
  const colorMap = Object.fromEntries(proveedores.map((p, i) => [p, COLORS[i % COLORS.length]]))

  const chartData = data.map((d) => ({
    x: new Date(d.fecha + 'T00:00:00').getTime(),
    y: d.precio,
    proveedor: d.proveedor,
    entidad: d.entidad,
    fecha: d.fecha,
  }))

  const formatY = (v: number) => {
    if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`
    if (v >= 1_000) return `${(v / 1_000).toFixed(0)}K`
    return String(v)
  }

  const formatX = (v: number) =>
    new Date(v).toLocaleDateString('es-BO', { month: 'short', year: '2-digit' })

  return (
    <ResponsiveContainer width="100%" height={280}>
      <ScatterChart margin={{ left: 8, right: 16, top: 8, bottom: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis
          dataKey="x"
          type="number"
          domain={['auto', 'auto']}
          tickFormatter={formatX}
          tick={{ fontSize: 11, fill: '#6b7280' }}
          axisLine={false}
          tickLine={false}
          scale="time"
        />
        <YAxis
          dataKey="y"
          tickFormatter={formatY}
          tick={{ fontSize: 11, fill: '#6b7280' }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          content={({ active, payload }) => {
            if (!active || !payload?.length) return null
            const d = payload[0].payload
            return (
              <div className="bg-white border border-gray-200 rounded-lg p-3 shadow text-xs space-y-1">
                <div className="font-medium text-gray-900">
                  Bs. {Number(d.y).toLocaleString('es-BO', { minimumFractionDigits: 2 })}
                </div>
                <div className="text-gray-500">{d.proveedor}</div>
                <div className="text-gray-400">{d.entidad}</div>
                <div className="text-gray-400">{new Date(d.x).toLocaleDateString('es-BO', { day: '2-digit', month: 'long', year: 'numeric' })}</div>
              </div>
            )
          }}
        />
        <Scatter data={chartData} isAnimationActive={false}>
          {chartData.map((d, i) => (
            <Cell key={i} fill={colorMap[d.proveedor]} opacity={0.85} />
          ))}
        </Scatter>
      </ScatterChart>
    </ResponsiveContainer>
  )
}
