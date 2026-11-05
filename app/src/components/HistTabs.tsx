'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useTransition } from 'react'

const TABS = [
  { href: '/historico', label: 'Resumen', exact: true },
  { href: '/historico/producto', label: 'Productos' },
  { href: '/historico/proveedor', label: 'Proveedores' },
]

/** Sub-pestañas del módulo Histórico + botón para actualizar los datos. */
export default function HistTabs() {
  const pathname = usePathname()
  const router = useRouter()
  const [isPending, startTransition] = useTransition()

  const isActive = (href: string, exact?: boolean) =>
    exact ? pathname === href : pathname === href || pathname.startsWith(href + '/')

  return (
    <div className="flex items-center justify-between gap-2 border-b border-gray-200 -mb-px">
      <nav className="flex items-center gap-1 overflow-x-auto no-scrollbar">
        {TABS.map((t) => {
          const active = isActive(t.href, t.exact)
          return (
            <Link
              key={t.href}
              href={t.href}
              className={`whitespace-nowrap px-3 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                active
                  ? 'border-blue-600 text-blue-700'
                  : 'border-transparent text-gray-500 hover:text-gray-800'
              }`}
            >
              {t.label}
            </Link>
          )
        })}
      </nav>
      <button
        onClick={() => startTransition(() => router.refresh())}
        disabled={isPending}
        className="shrink-0 inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-gray-600
                   rounded-lg hover:bg-gray-100 disabled:opacity-60 transition-colors"
        title="Actualizar datos"
        aria-label="Actualizar datos"
      >
        <svg
          className={`w-3.5 h-3.5 ${isPending ? 'animate-spin' : ''}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
        </svg>
        <span className="hidden sm:inline">{isPending ? 'Actualizando…' : 'Actualizar'}</span>
      </button>
    </div>
  )
}
