import { Suspense } from 'react'
import Link from 'next/link'
import SearchFilters from '@/components/SearchFilters'
import ProcesosTable from '@/components/ProcesosTable'
import Pagination from '@/components/Pagination'
import { getProcesos, getEntidades } from '@/lib/queries'
import { type SearchParams } from '@/lib/types'

type Props = {
  searchParams: Promise<SearchParams>
}

export default async function Home({ searchParams }: Props) {
  const params = await searchParams
  const page = Number(params.page ?? 1)

  const [{ data: procesos, count }, entidades] = await Promise.all([
    getProcesos(params),
    getEntidades(),
  ])

  const total = count ?? 0

  return (
    <main className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                <span className="text-white text-xs font-bold">S</span>
              </div>
              <div>
                <h1 className="text-lg font-semibold text-gray-900">SICOES Intelligence</h1>
                <p className="text-xs text-gray-500">Contrataciones estatales de Bolivia</p>
              </div>
            </div>
            <nav className="flex items-center gap-4 text-sm">
              <Link href="/" className="text-blue-600 font-medium">Procesos</Link>
              <Link href="/items" className="text-gray-500 hover:text-gray-800">Bienes</Link>
              <Link href="/dashboard" className="text-gray-500 hover:text-gray-800">Dashboard</Link>
            </nav>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-6">
        {/* Filtros */}
        <SearchFilters entidades={entidades} current={params} />

        {/* Resultados */}
        <ProcesosTable procesos={procesos ?? []} />

        {/* Paginación */}
        <Suspense>
          <Pagination total={total} currentPage={page} />
        </Suspense>
      </div>
    </main>
  )
}
