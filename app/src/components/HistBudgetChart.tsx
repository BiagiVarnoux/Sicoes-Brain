'use client'

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'

type Row = { anio: number; referencial: number; adjudicado: number; ejecutado: number }

// Tres medidas fijas, colores asignados por significado (no por rango).
const REF = '#94a3b8' // presupuestado → gris neutro (línea base)
const ADJ = '#2a78d6' // adjudicado    → azul
const EJE = '#1baf7a' // ejecutado     → aqua

function fmt(v: number): string {
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`
  if (v >= 1_000) return `${(v / 1_000).toFixed(0)}K`
  return String(Math.round(v))
}

/** Presupuestado vs adjudicado vs ejecutado por año (3 series → leyenda). */
export default function HistBudgetChart({ data }: { data: Row[] }) {
  const chart = data.map((d) => ({ ...d, label: String(d.anio) }))

  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={chart} margin={{ left: 0, right: 8, top: 4, bottom: 4 }} barGap={2}>
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
        <XAxis dataKey="label" tick={{ fontSize: 11, fill: '#6b7280' }} axisLine={false} tickLine={false} interval={0} />
        <YAxis tickFormatter={fmt} tick={{ fontSize: 10, fill: '#9ca3af' }} axisLine={false} tickLine={false} width={40} />
        <Tooltip
          formatter={(v, name) => [`Bs. ${Number(v).toLocaleString('es-BO', { maximumFractionDigits: 0 })}`, name]}
          contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #e5e7eb' }}
          cursor={{ fill: '#f9fafb' }}
        />
        <Legend wrapperStyle={{ fontSize: 11 }} iconType="circle" iconSize={8} />
        <Bar dataKey="referencial" name="Presupuestado" fill={REF} radius={[3, 3, 0, 0]} maxBarSize={28} isAnimationActive={false} />
        <Bar dataKey="adjudicado" name="Adjudicado" fill={ADJ} radius={[3, 3, 0, 0]} maxBarSize={28} isAnimationActive={false} />
        <Bar dataKey="ejecutado" name="Ejecutado" fill={EJE} radius={[3, 3, 0, 0]} maxBarSize={28} isAnimationActive={false} />
      </BarChart>
    </ResponsiveContainer>
  )
}
