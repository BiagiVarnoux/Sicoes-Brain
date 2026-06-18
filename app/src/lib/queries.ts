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

export async function getItemsByProceso(cuce: string) {
  const { data } = await supabase
    .from('items')
    .select(`
      id, nro_item, unspsc_codigo, descripcion_producto,
      unidad_medida, cantidad, precio_referencial, precio_adjudicado,
      monto_total, origen, estado_item, fuente_formulario,
      proveedor_id,
      unspsc_catalogo ( producto_nombre, clase_nombre, familia_nombre ),
      proveedores ( nombre )
    `)
    .eq('cuce', cuce)
    .order('nro_item')
  return data ?? []
}

export async function getEntidades() {
  const { data } = await supabase
    .from('entidades')
    .select('codigo,nombre,departamento')
    .order('nombre')
  return data ?? []
}

export async function getKPIsGlobales() {
  const { data } = await supabase.rpc('get_kpis_globales')
  const kpis = data as {
    total_procesos: number
    monto_total: number
    total_items: number
    total_proveedores: number
  } | null
  return {
    totalProcesos: kpis?.total_procesos ?? 0,
    montoTotal: Number(kpis?.monto_total ?? 0),
    totalItems: kpis?.total_items ?? 0,
    totalProveedores: kpis?.total_proveedores ?? 0,
  }
}

export async function getProcesosporModalidad() {
  const { data } = await supabase.rpc('get_procesos_por_modalidad')
  return (data ?? []) as { modalidad: string; total: number }[]
}

export async function getProcesosporEstado() {
  const { data } = await supabase.rpc('get_procesos_por_estado')
  return (data ?? []) as { estado: string; total: number }[]
}

export async function getTopEntidadesPorMonto(limit = 10) {
  const { data } = await supabase.rpc('get_top_entidades_por_monto', { limit_n: limit })
  return (data ?? []) as { entidad: string; monto: number }[]
}
