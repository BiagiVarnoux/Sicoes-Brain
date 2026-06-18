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
  const [
    { count: totalProcesos },
    { data: montoData },
    { count: totalItems },
    { count: totalProveedores },
  ] = await Promise.all([
    supabase.from('procesos').select('*', { count: 'exact', head: true }),
    supabase.from('procesos').select('monto_adjudicado').not('monto_adjudicado', 'is', null),
    supabase.from('items').select('*', { count: 'exact', head: true }),
    supabase.from('proveedores').select('*', { count: 'exact', head: true }),
  ])

  const montoTotal = (montoData ?? []).reduce(
    (sum, r) => sum + (r.monto_adjudicado ?? 0), 0
  )

  return {
    totalProcesos: totalProcesos ?? 0,
    montoTotal,
    totalItems: totalItems ?? 0,
    totalProveedores: totalProveedores ?? 0,
  }
}

export async function getProcesosporModalidad() {
  const { data } = await supabase
    .from('procesos')
    .select('modalidad')
  if (!data) return []
  const counts: Record<string, number> = {}
  for (const r of data) {
    const m = r.modalidad ?? 'Sin datos'
    counts[m] = (counts[m] ?? 0) + 1
  }
  return Object.entries(counts)
    .map(([modalidad, total]) => ({ modalidad, total }))
    .sort((a, b) => b.total - a.total)
}

export async function getProcesosporEstado() {
  const { data } = await supabase
    .from('procesos')
    .select('estado')
  if (!data) return []
  const counts: Record<string, number> = {}
  for (const r of data) {
    const e = r.estado ?? 'Sin datos'
    counts[e] = (counts[e] ?? 0) + 1
  }
  return Object.entries(counts)
    .map(([estado, total]) => ({ estado, total }))
    .sort((a, b) => b.total - a.total)
}

export async function getTopEntidadesPorMonto(limit = 10) {
  const { data } = await supabase
    .from('procesos')
    .select('entidad_nombre,monto_adjudicado')
    .not('monto_adjudicado', 'is', null)
  if (!data) return []
  const montos: Record<string, number> = {}
  for (const r of data) {
    const e = r.entidad_nombre ?? 'Sin nombre'
    montos[e] = (montos[e] ?? 0) + (r.monto_adjudicado ?? 0)
  }
  return Object.entries(montos)
    .map(([entidad, monto]) => ({ entidad, monto }))
    .sort((a, b) => b.monto - a.monto)
    .slice(0, limit)
}
