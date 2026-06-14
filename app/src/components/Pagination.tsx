'use client'

import { useRouter, usePathname, useSearchParams } from 'next/navigation'
import { PAGE_SIZE } from '@/lib/types'

type Props = {
  total: number
  currentPage: number
}

export default function Pagination({ total, currentPage }: Props) {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const totalPages = Math.ceil(total / PAGE_SIZE)

  if (totalPages <= 1) return null

  const go = (page: number) => {
    const params = new URLSearchParams(searchParams.toString())
    params.set('page', String(page))
    router.push(`${pathname}?${params.toString()}`)
  }

  // Mostrar máximo 7 páginas alrededor de la actual
  const pages: (number | '...')[] = []
  if (totalPages <= 7) {
    for (let i = 1; i <= totalPages; i++) pages.push(i)
  } else {
    pages.push(1)
    if (currentPage > 3) pages.push('...')
    for (let i = Math.max(2, currentPage - 1); i <= Math.min(totalPages - 1, currentPage + 1); i++) {
      pages.push(i)
    }
    if (currentPage < totalPages - 2) pages.push('...')
    pages.push(totalPages)
  }

  return (
    <div className="flex items-center justify-between text-sm text-gray-600">
      <span>
        {total.toLocaleString('es-BO')} procesos — página {currentPage} de {totalPages}
      </span>
      <div className="flex gap-1">
        <button
          onClick={() => go(currentPage - 1)}
          disabled={currentPage === 1}
          className="px-3 py-1.5 rounded-lg border border-gray-200 disabled:opacity-40 hover:bg-gray-50"
        >
          ‹
        </button>
        {pages.map((p, i) =>
          p === '...' ? (
            <span key={`dots-${i}`} className="px-2 py-1.5">…</span>
          ) : (
            <button
              key={p}
              onClick={() => go(p)}
              className={`px-3 py-1.5 rounded-lg border ${
                p === currentPage
                  ? 'bg-blue-600 text-white border-blue-600'
                  : 'border-gray-200 hover:bg-gray-50'
              }`}
            >
              {p}
            </button>
          )
        )}
        <button
          onClick={() => go(currentPage + 1)}
          disabled={currentPage === totalPages}
          className="px-3 py-1.5 rounded-lg border border-gray-200 disabled:opacity-40 hover:bg-gray-50"
        >
          ›
        </button>
      </div>
    </div>
  )
}
