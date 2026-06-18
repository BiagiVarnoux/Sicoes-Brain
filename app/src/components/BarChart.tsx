'use client'

import {
  BarChart as ReBarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'

type DataItem = { label: string; value: number }

type Props = {
  data: DataItem[]
  color?: string
  layout?: 'vertical' | 'horizontal'
  formatValue?: (v: number) => string
}

const BLUE = '#2563eb'

export default function BarChart({ data, color = BLUE, layout = 'horizontal', formatValue }: Props) {
  if (layout === 'vertical') {
    return (
      <ResponsiveContainer width="100%" height={Math.max(data.length * 36, 200)}>
        <ReBarChart data={data} layout="vertical" margin={{ left: 8, right: 24, top: 4, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f0f0f0" />
          <XAxis
            type="number"
            tick={{ fontSize: 11, fill: '#6b7280' }}
            tickFormatter={formatValue}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="label"
            width={180}
            tick={{ fontSize: 11, fill: '#374151' }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            formatter={(v) => {
              const n = typeof v === 'number' ? v : Number(v)
              return [formatValue ? formatValue(n) : n.toLocaleString('es-BO'), '']
            }}
            contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e5e7eb' }}
            cursor={{ fill: '#f9fafb' }}
          />
          <Bar dataKey="value" radius={[0, 4, 4, 0]} maxBarSize={24}>
            {data.map((_, i) => (
              <Cell key={i} fill={color} opacity={1 - i * 0.06} />
            ))}
          </Bar>
        </ReBarChart>
      </ResponsiveContainer>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <ReBarChart data={data} margin={{ left: 0, right: 8, top: 4, bottom: 24 }}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
        <XAxis
          dataKey="label"
          tick={{ fontSize: 11, fill: '#6b7280' }}
          axisLine={false}
          tickLine={false}
          angle={-30}
          textAnchor="end"
          interval={0}
        />
        <YAxis
          tick={{ fontSize: 11, fill: '#6b7280' }}
          axisLine={false}
          tickLine={false}
          tickFormatter={formatValue}
        />
        <Tooltip
          formatter={(v) => {
            const n = typeof v === 'number' ? v : Number(v)
            return [formatValue ? formatValue(n) : n.toLocaleString('es-BO'), '']
          }}
          contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e5e7eb' }}
          cursor={{ fill: '#f9fafb' }}
        />
        <Bar dataKey="value" radius={[4, 4, 0, 0]} maxBarSize={48} fill={color} />
      </ReBarChart>
    </ResponsiveContainer>
  )
}
