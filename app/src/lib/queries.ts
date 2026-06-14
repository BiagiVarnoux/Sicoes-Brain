import { supabase } from './supabase'
import { PAGE_SIZE, type SearchParams } from './types'

export async function getProcesos(params: SearchParams) {
  const page = Number(params.page ?? 1)
  const from = (page - 1) * PAGE_SIZE
  const to = from + PAGE_SIZE - 1

  let query = supabase
    .from('procesos')
    .select('cuce,entidad_codigo,entidad_nombre,objeto,modalidad,estado,fecha_publicacion,fecha_presentacion,monto_referencial,monto_adjudicado,tipo_contratacion', { count: 'exact' })
    .order('fecha_publicacion', { ascending: false })
    .range(from, to)

  if (params.q) {
    query = query.ilike('objeto', `%${params.q}%`)
  }
  if (params.modalidad) {
    query = query.eq('modalidad', params.modalidad)
  }
  if (params.estado) {
    query = query.eq('estado', params.estado)
  }
  if (params.entidad) {
    query = query.eq('entidad_codigo', params.entidad)
  }

  return query
}

export async function getProcesoBySlug(cuce: string) {
  const { data, error } = await supabase
    .from('procesos')
    .select('*')
    .eq('cuce', cuce)
    .single()

  if (error) return null
  return data
}

export async function getEntidades() {
  const { data } = await supabase
    .from('entidades')
    .select('codigo,nombre,departamento')
    .order('nombre')
  return data ?? []
}
