import { Suspense } from 'react'
import SearchFilters from '@/components/SearchFilters'
import ProcesosTable from '@/components/ProcesosTable'
import Pagination from '@/components/Pagination'
import SiteHeader from '@/components/SiteHeader'
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
      <SiteHeader maxWidth="max-w-7xl" />

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
