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
  const { data } = await supabase.rpc('get_items_by_proceso', { p_cuce: cuce })
  return (data ?? []) as {
    id: number
    nro_item: number
    unspsc_codigo: string | null
    descripcion_producto: string
    unidad_medida: string | null
    cantidad: number | null
    precio_referencial: number | null
    precio_adjudicado: number | null
    monto_total: number | null
    estado_item: string
    fuente_formulario: string
    clase_nombre: string | null
    familia_nombre: string | null
    proveedor_nombre: string | null
  }[]
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

export async function getKPIsFiltrados(anio?: number | null, entidad?: string) {
  const { data } = await supabase.rpc('get_kpis_filtrados', {
    p_anio: anio ?? null,
    p_entidad: entidad ?? '',
  })
  const rows = data as { total_procesos: number; monto_total: number; total_items: number; total_proveedores: number }[] | null
  const kpis = rows?.[0]
  return {
    totalProcesos: Number(kpis?.total_procesos ?? 0),
    montoTotal: Number(kpis?.monto_total ?? 0),
    totalItems: Number(kpis?.total_items ?? 0),
    totalProveedores: Number(kpis?.total_proveedores ?? 0),
  }
}

export async function getAniosDisponibles() {
  const { data } = await supabase.rpc('get_anios_disponibles')
  return (data ?? []) as { anio: number }[]
}

export async function getProcesosporModalidad() {
  const { data } = await supabase.rpc('get_procesos_por_modalidad')
  return (data ?? []) as { modalidad: string; total: number }[]
}

export async function getProcesosporEstado() {
  const { data } = await supabase.rpc('get_procesos_por_estado')
  return (data ?? []) as { estado: string; total: number }[]
}

export async function getTopEntidadesPorMonto(limit = 10, anio?: number | null) {
  const { data } = await supabase.rpc('get_top_entidades_por_monto', { limit_n: limit, p_anio: anio ?? null })
  return (data ?? []) as { entidad: string; monto: number }[]
}

export async function getTopProductos(params?: {
  limit?: number
  q?: string
  entidad?: string
  orderBy?: 'monto' | 'veces' | 'cantidad'
  anio?: number | null
}) {
  const { data } = await supabase.rpc('get_top_productos', {
    limit_n:   params?.limit    ?? 50,
    q:         params?.q        ?? '',
    p_entidad: params?.entidad  ?? '',
    order_by:  params?.orderBy  ?? 'monto',
    p_anio:    params?.anio     ?? null,
  })
  return (data ?? []) as {
    descripcion: string
    clase: string
    veces: number
    compras: number
    monto_total: number
    precio_min: number
    precio_max: number
  }[]
}

export async function getTopProveedores(limit = 10, anio?: number | null, entidad?: string) {
  const { data } = await supabase.rpc('get_top_proveedores', { limit_n: limit, p_anio: anio ?? null, p_entidad: entidad ?? '' })
  return (data ?? []) as { proveedor_id: number; proveedor: string; contratos: number; monto_total: number }[]
}

export async function getProveedorStats(id: number) {
  const { data } = await supabase.rpc('get_proveedor_stats', { p_id: id })
  const d = data as {
    nombre: string; monto_total: number; total_contratos: number
    total_entidades: number; total_productos: number
  } | null
  return d
}

export async function getProveedorContratos(id: number) {
  const { data } = await supabase.rpc('get_proveedor_contratos', { p_id: id })
  return (data ?? []) as {
    cuce: string; descripcion_producto: string; unidad_medida: string | null
    cantidad: number | null; precio_adjudicado: number | null; monto_total: number | null
    entidad_nombre: string; fecha_publicacion: string | null; modalidad: string | null
  }[]
}

export async function getProveedorTopProductos(id: number) {
  const { data } = await supabase.rpc('get_proveedor_top_productos', { p_id: id, limit_n: 10 })
  return (data ?? []) as {
    descripcion: string; veces: number; monto_total: number
    precio_min: number; precio_max: number
  }[]
}

export async function getProveedorById(id: number) {
  const { data } = await supabase.from('proveedores').select('id,nombre').eq('id', id).single()
  return data as { id: number; nombre: string } | null
}

export type ItemRow = {
  id: number
  cuce: string
  nro_item: number
  descripcion_producto: string
  unidad_medida: string
  cantidad: number
  precio_referencial: number | null
  precio_adjudicado: number | null
  monto_total: number | null
  estado_item: string
  fuente_formulario: string
  unspsc_codigo: string | null
  clase_nombre: string | null
  familia_nombre: string | null
  proveedor_nombre: string | null
  entidad_nombre: string | null
  fecha_publicacion: string | null
  modalidad: string | null
}

export type ProductoHistorialRow = {
  id: number
  cuce: string
  nro_item: number
  unidad_medida: string
  cantidad: number
  precio_referencial: number | null
  precio_adjudicado: number | null
  monto_total: number | null
  estado_item: string
  fuente_formulario: string
  unspsc_codigo: string | null
  clase_nombre: string | null
  familia_nombre: string | null
  proveedor_id: number | null
  proveedor_nombre: string | null
  entidad_nombre: string | null
  entidad_codigo: string | null
  fecha_publicacion: string | null
  modalidad: string | null
}

export type ProductoStats = {
  total_compras: number
  total_adjudicadas: number
  cantidad_total: number
  monto_total: number
  precio_min: number | null
  precio_max: number | null
  precio_promedio: number | null
  total_proveedores: number
  total_entidades: number
}

export async function getProductoHistorial(descripcion: string) {
  const { data } = await supabase.rpc('get_producto_historial', { p_descripcion: descripcion })
  return (data ?? []) as ProductoHistorialRow[]
}

export async function getProductoStats(descripcion: string) {
  const { data } = await supabase.rpc('get_producto_stats', { p_descripcion: descripcion })
  const row = (data as ProductoStats[] | null)?.[0]
  return row ?? null
}

export async function getMontoPorMes() {
  const { data } = await supabase.rpc('get_monto_por_mes')
  return (data ?? []) as { anio: number; mes: number; monto: number; total_items: number }[]
}

export async function searchItems(params: {
  q?: string
  entidad?: string
  estado?: string
  page?: number
}) {
  const page = Number(params.page ?? 1)
  const limit = 50
  const offset = (page - 1) * limit

  const [{ data }, { data: countData }] = await Promise.all([
    supabase.rpc('search_items', {
      q: params.q ?? '',
      p_entidad: params.entidad ?? '',
      p_estado: params.estado ?? '',
      p_limit: limit,
      p_offset: offset,
    }),
    supabase.rpc('search_items_count', {
      q: params.q ?? '',
      p_entidad: params.entidad ?? '',
      p_estado: params.estado ?? '',
    }),
  ])

  return {
    items: (data ?? []) as ItemRow[],
    total: Number(countData ?? 0),
    page,
    pages: Math.ceil(Number(countData ?? 0) / limit),
  }
}
