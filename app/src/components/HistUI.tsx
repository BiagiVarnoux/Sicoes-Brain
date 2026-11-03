import Link from 'next/link'
import { fmtMonto } from '@/lib/historico'

export function StatCard({ label, value, sub, color }: { label: string; value: string; sub?: string; color: string }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5">
      <div className={`w-8 h-1 rounded-full mb-3 ${color}`} />
      <div className="text-2xl font-bold text-gray-900 tabular-nums">{value}</div>
      <div className="text-sm font-medium text-gray-600 mt-1">{label}</div>
      {sub && <div className="text-xs text-gray-400 mt-0.5">{sub}</div>}
    </div>
  )
}

export function SectionTitle({ children, hint }: { children: React.ReactNode; hint?: string }) {
  return (
    <div className="mb-3">
      <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">{children}</h2>
      {hint && <p className="text-xs text-gray-400 mt-0.5">{hint}</p>}
    </div>
  )
}

export function Card({ title, children, right }: { title?: string; children: React.ReactNode; right?: React.ReactNode }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      {title && (
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-gray-700">{title}</h3>
          {right}
        </div>
      )}
      {children}
    </div>
  )
}

export function ProvisionalBadge({ className = '' }: { className?: string }) {
  return (
    <span
      className={`inline-flex items-center gap-1 text-[10px] font-medium text-amber-700 bg-amber-50
                  border border-amber-200 rounded-full px-2 py-0.5 ${className}`}
      title="Agrupado por UNSPSC/descripción. Se consolidará cuando corra la canonicalización por IA."
    >
      <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
      provisional
    </span>
  )
}

/** Lista horizontal de barras (ranking) con enlace opcional por fila. */
export function RankList({
  rows,
  hrefOf,
  fmt = fmtMonto,
  emptyLabel = 'Sin datos',
}: {
  rows: { key: string; label: string; value: number; sub?: string; provisional?: boolean }[]
  hrefOf?: (key: string) => string
  fmt?: (n: number) => string
  emptyLabel?: string
}) {
  if (rows.length === 0) return <p className="text-sm text-gray-400 py-6 text-center">{emptyLabel}</p>
  const max = Math.max(...rows.map((r) => r.value), 1)
  return (
    <div className="space-y-2">
      {rows.map((r) => {
        const pct = Math.round((r.value / max) * 100)
        const inner = (
          <>
            <div className="flex items-baseline justify-between gap-2 mb-1">
              <span className="text-xs font-medium text-gray-700 truncate flex items-center gap-1.5">
                {r.label}
                {r.provisional && <ProvisionalBadge />}
              </span>
              <span className="text-xs font-semibold text-emerald-700 tabular-nums shrink-0">{fmt(r.value)}</span>
            </div>
            <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
              <div className="h-full bg-blue-500 rounded-full" style={{ width: `${pct}%` }} />
            </div>
            {r.sub && <div className="text-[11px] text-gray-400 mt-0.5">{r.sub}</div>}
          </>
        )
        return hrefOf ? (
          <Link key={r.key} href={hrefOf(r.key)} className="block group hover:bg-gray-50 -mx-2 px-2 py-1 rounded-lg transition-colors">
            {inner}
          </Link>
        ) : (
          <div key={r.key} className="py-1">{inner}</div>
        )
      })}
    </div>
  )
}
