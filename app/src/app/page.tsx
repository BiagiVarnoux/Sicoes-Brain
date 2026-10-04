import { redirect } from 'next/navigation'

// La página principal ahora es el Radar. La lista histórica de Procesos sigue
// disponible en /procesos (no se eliminó), pero no se enlaza desde el nav.
export default function Home() {
  redirect('/radar')
}
