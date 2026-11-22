import { redirect } from 'next/navigation'

// La pestaña "Análisis" se fusionó dentro de la vista de producto
// (/historico/producto/[key]), que ahora trae los filtros entidad × año y todo
// el análisis. Esta ruta queda sólo como redirección para enlaces viejos.
type Props = { searchParams: Promise<{ producto?: string; entidades?: string }> }

export default async function AnalisisRedirect({ searchParams }: Props) {
  const sp = await searchParams
  if (sp.producto) {
    const qs = sp.entidades ? `?entidades=${encodeURIComponent(sp.entidades)}` : ''
    redirect(`/historico/producto/${encodeURIComponent(sp.producto)}${qs}`)
  }
  redirect('/historico/producto')
}
