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

type Item = { label: string; value: number; contratos: number }

const COLORS = ['#2563eb', '#3b82f6', '#60a5fa', '#93c5fd', '#bfdbfe', '#dbeafe', '#eff6ff', '#2563eb', '#1d4ed8', '#1e40af']

export default function ProveedoresChart({ data }: { data: Item[] }) {
  const fmt = (v: number) => {
    if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`
    if (v >= 1_000) return `${(v / 1_000).toFixed(0)}K`
    return String(v)
  }

  const truncate = (s: string) => s.length > 28 ? s.slice(0, 26) + '…' : s

  return (
    <ResponsiveContainer width="100%" height={Math.max(data.length * 40, 160)}>
      <BarChart
        data={data.map((d) => ({ ...d, label: truncate(d.label) }))}
        layout="vertical"
        margin={{ left: 8, right: 32, top: 4, bottom: 4 }}
      >
        <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f0f0f0" />
        <XAxis
          type="number"
          tick={{ fontSize: 11, fill: '#6b7280' }}
          tickFormatter={fmt}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          type="category"
          dataKey="label"
          width={200}
          tick={{ fontSize: 11, fill: '#374151' }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          formatter={(v, _, props) => [
            `Bs. ${Number(v).toLocaleString('es-BO')} · ${props.payload.contratos} contrato${props.payload.contratos !== 1 ? 's' : ''}`,
            '',
          ]}
          contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e5e7eb' }}
          cursor={{ fill: '#f9fafb' }}
        />
        <Bar dataKey="value" radius={[0, 4, 4, 0]} maxBarSize={28}>
          {data.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
