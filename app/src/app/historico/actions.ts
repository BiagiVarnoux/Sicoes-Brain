'use server'

import { bustHistCache } from '@/lib/historico'

/** Invalida el caché en proceso de los datos históricos. Lo llama el botón
 *  "Actualizar" de HistTabs antes de refrescar la vista, para forzar una
 *  re-descarga fresca de las tablas hist_*. */
export async function refreshHist(): Promise<void> {
  bustHistCache()
}
