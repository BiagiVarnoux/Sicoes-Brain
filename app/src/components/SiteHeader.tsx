'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'

const NAV = [
  { href: '/', label: 'Procesos' },
  { href: '/items', label: 'Bienes' },
  { href: '/dashboard', label: 'Dashboard' },
]

interface Props {
  /** Ancho máximo del contenedor; debe coincidir con el de la página. */
  maxWidth?: 'max-w-5xl' | 'max-w-6xl' | 'max-w-7xl'
}

export default function SiteHeader({ maxWidth = 'max-w-6xl' }: Props) {
  const pathname = usePathname()

  const isActive = (href: string) =>
    href === '/' ? pathname === '/' || pathname.startsWith('/proceso')
                 : pathname.startsWith(href)

  return (
    <header className="sticky top-0 z-30 bg-white/90 backdrop-blur border-b border-gray-200">
      <div className={`${maxWidth} mx-auto px-4 sm:px-6 py-4 flex items-center justify-between`}>
        <Link href="/" className="flex items-center gap-3 group">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center
                          group-hover:bg-blue-700 transition-colors">
            <span className="text-white text-xs font-bold">S</span>
          </div>
          <div>
            <h1 className="text-lg font-semibold text-gray-900 leading-tight">SICOES Intelligence</h1>
            <p className="text-xs text-gray-500 leading-tight">Contrataciones estatales de Bolivia</p>
          </div>
        </Link>
        <nav className="flex items-center gap-1 text-sm">
          {NAV.map((n) => (
            <Link
              key={n.href}
              href={n.href}
              className={`px-3 py-1.5 rounded-lg transition-colors ${
                isActive(n.href)
                  ? 'bg-blue-50 text-blue-700 font-medium'
                  : 'text-gray-500 hover:text-gray-800 hover:bg-gray-50'
              }`}
            >
              {n.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  )
}
