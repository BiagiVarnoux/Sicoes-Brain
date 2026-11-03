import { supabase } from './supabase'

// ─────────────────────────────────────────────────────────────────────────────
// Dashboard histórico — capa de datos.
//
// Patrón igual a /metricas: consultas directas con el cliente Supabase (lectura
// pública anon) + agregación en TypeScript. Las tablas hist_* las puebla un
// scraper aparte; acá sólo se leen.
//
// Dos ejes de análisis, igual de importantes:
//   1) POR ENTIDAD   — qué pide una entidad en el tiempo.
//   2) POR PRODUCTO  — cuánto piden del mismo bien todas las entidades (cross).
//
// La agrupación de producto usa producto_canonico_id cuando existe; mientras la
// canonicalización por IA no corre, cae a unspsc_codigo y luego a la descripción
// normalizada. Esos grupos quedan marcados como `provisional` para la UI.
// ─────────────────────────────────────────────────────────────────────────────

export type HistProceso = {
  cuce: string
  entidad_codigo: string
  entidad_nombre: string | null
  modalidad: string | null
  objeto: string | null
  cuce_anio: number | null
  fecha_publicacion: string | null
  fecha_firma_contrato: string | null
  fecha_entrega: string | null
  monto_adjudicado: number | null
  tiene_dbc: boolean | null
}

export type HistItem = {
  id: number
  cuce: string
  nro_item: number | null
  unspsc_codigo: string | null
  descripcion: string | null
  unidad_medida: string | null
  cantidad: number | null
  precio_referencial: number | null
  precio_adjudicado: number | null
  monto_total: number | null
  proveedor: string | null
  estado_recepcion: string | null
  cantidad_recibida: number | null
  monto_ejecutado: number | null
  fecha_entrega: string | null
  entidad_codigo: string | null
  modalidad: string | null
  fecha_publicacion: string | null
  producto_canonico_id: number | null
}

export type HistCanonico = {
  id: number
  nombre_canonico: string
  categoria: string | null
  unspsc_codigo: string | null
}

export type HistData = {
  procesos: HistProceso[]
  items: HistItem[]
  canonicos: Map<number, HistCanonico>
  /** entidad_codigo → nombre (resuelto desde hist_procesos). */
  entidadNombre: Map<string, string>
  entidades: { codigo: string; nombre: string }[]
  anios: number[]
}

// ─── Fetch ───────────────────────────────────────────────────────────────────

const PROCESO_COLS =
  'cuce,entidad_codigo,entidad_nombre,modalidad,objeto,cuce_anio,fecha_publicacion,fecha_firma_contrato,fecha_entrega,monto_adjudicado,tiene_dbc'
const ITEM_COLS =
  'id,cuce,nro_item,unspsc_codigo,descripcion,unidad_medida,cantidad,precio_referencial,precio_adjudicado,monto_total,proveedor,estado_recepcion,cantidad_recibida,monto_ejecutado,fecha_entrega,entidad_codigo,modalidad,fecha_publicacion,producto_canonico_id'

/** Lee una tabla completa salteando el tope de 1000 filas de PostgREST. */
async function fetchAll<T>(table: string, columns: string): Promise<T[]> {
  const pageSize = 1000
  const all: T[] = []
  for (let from = 0; ; from += pageSize) {
    const { data, error } = await supabase
      .from(table)
      .select(columns)
      .range(from, from + pageSize - 1)
    if (error || !data || data.length === 0) break
    all.push(...(data as T[]))
    if (data.length < pageSize) break
  }
  return all
}

export async function getHistData(): Promise<HistData> {
  const [procesos, items, canonRows] = await Promise.all([
    fetchAll<HistProceso>('hist_procesos', PROCESO_COLS),
    fetchAll<HistItem>('hist_items', ITEM_COLS),
    fetchAll<HistCanonico>('hist_productos_canonicos', 'id,nombre_canonico,categoria,unspsc_codigo'),
  ])

  const canonicos = new Map<number, HistCanonico>()
  for (const c of canonRows) canonicos.set(c.id, c)

  const entidadNombre = new Map<string, string>()
  for (const p of procesos) {
    if (p.entidad_codigo && p.entidad_nombre && !entidadNombre.has(p.entidad_codigo)) {
      entidadNombre.set(p.entidad_codigo, p.entidad_nombre)
    }
  }

  const entidades = Array.from(entidadNombre.entries())
    .map(([codigo, nombre]) => ({ codigo, nombre }))
    .sort((a, b) => a.nombre.localeCompare(b.nombre, 'es'))

  const anioSet = new Set<number>()
  for (const p of procesos) {
    const a = p.cuce_anio ?? yearOf(p.fecha_publicacion)
    if (a) anioSet.add(a)
  }
  const anios = Array.from(anioSet).sort((a, b) => b - a)

  return { procesos, items, canonicos, entidadNombre, entidades, anios }
}

// ─── Utilidades ────────────────────────────────────────────────────────────

export const num = (v: number | null | undefined): number => (v == null ? 0 : Number(v) || 0)

export function yearOf(fecha: string | null | undefined): number | null {
  if (!fecha) return null
  const y = Number(fecha.slice(0, 4))
  return Number.isFinite(y) && y > 1900 ? y : null
}

function normDesc(s: string | null | undefined): string {
  return (s ?? '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
}

/** Año del ítem para filtros/series: fecha_publicacion (cae al año del proceso). */
export function itemAnio(it: HistItem, procByCuce: Map<string, HistProceso>): number | null {
  return (
    yearOf(it.fecha_publicacion) ??
    procByCuce.get(it.cuce)?.cuce_anio ??
    yearOf(procByCuce.get(it.cuce)?.fecha_publicacion ?? null)
  )
}

// ─── Agrupación de producto (provisional hasta la canonicalización) ──────────

/** Llave de agrupación estable de un ítem. */
export function productoKey(it: HistItem): string {
  if (it.producto_canonico_id != null) return `c:${it.producto_canonico_id}`
  if (it.unspsc_codigo && it.unspsc_codigo.trim()) return `u:${it.unspsc_codigo.trim()}`
  return `d:${normDesc(it.descripcion)}`
}

export function isProvisional(key: string): boolean {
  return !key.startsWith('c:')
}

export type ProductoGrupo = {
  key: string
  label: string
  categoria: string | null
  unspsc: string | null
  provisional: boolean
  items: HistItem[]
}

/** Agrupa ítems en productos. La etiqueta sale del canónico o de la descripción
 *  más frecuente del grupo. */
export function agruparProductos(items: HistItem[], canonicos: Map<number, HistCanonico>): Map<string, ProductoGrupo> {
  const grupos = new Map<string, ProductoGrupo>()
  for (const it of items) {
    const key = productoKey(it)
    let g = grupos.get(key)
    if (!g) {
      g = {
        key,
        label: '',
        categoria: null,
        unspsc: it.unspsc_codigo?.trim() || null,
        provisional: isProvisional(key),
        items: [],
      }
      grupos.set(key, g)
    }
    g.items.push(it)
    if (!g.unspsc && it.unspsc_codigo) g.unspsc = it.unspsc_codigo.trim()
  }

  for (const g of grupos.values()) {
    if (g.key.startsWith('c:')) {
      const c = canonicos.get(Number(g.key.slice(2)))
      g.label = c?.nombre_canonico ?? g.items[0]?.descripcion ?? '(sin nombre)'
      g.categoria = c?.categoria ?? null
      if (c?.unspsc_codigo) g.unspsc = c.unspsc_codigo
    } else {
      g.label = descripcionRepresentativa(g.items)
    }
  }
  return grupos
}

/** Descripción más frecuente (desempata por la más larga). */
function descripcionRepresentativa(items: HistItem[]): string {
  const freq = new Map<string, number>()
  for (const it of items) {
    const d = (it.descripcion ?? '').trim()
    if (d) freq.set(d, (freq.get(d) ?? 0) + 1)
  }
  let best = ''
  let bestN = 0
  for (const [d, n] of freq) {
    if (n > bestN || (n === bestN && d.length > best.length)) {
      best = d
      bestN = n
    }
  }
  return best || '(sin descripción)'
}

// ─── Series y estadística ────────────────────────────────────────────────────

export type SerieMensual = { ym: string; anio: number; mes: number; monto: number; items: number; cantidad: number }

/** Serie mensual por fecha de publicación (adjudicación). */
export function serieMensual(items: HistItem[], procByCuce: Map<string, HistProceso>): SerieMensual[] {
  const map = new Map<string, SerieMensual>()
  for (const it of items) {
    const fecha = it.fecha_publicacion ?? procByCuce.get(it.cuce)?.fecha_publicacion ?? null
    if (!fecha) continue
    const anio = Number(fecha.slice(0, 4))
    const mes = Number(fecha.slice(5, 7))
    if (!anio || !mes) continue
    const ym = `${anio}-${String(mes).padStart(2, '0')}`
    const row = map.get(ym) ?? { ym, anio, mes, monto: 0, items: 0, cantidad: 0 }
    row.monto += num(it.monto_total) || num(it.precio_adjudicado) * num(it.cantidad)
    row.items += 1
    row.cantidad += num(it.cantidad)
    map.set(ym, row)
  }
  return Array.from(map.values()).sort((a, b) => a.ym.localeCompare(b.ym))
}

/** Estacionalidad por mes del año. Usa fecha_entrega (FORM500) cuando existe,
 *  cae a fecha_publicacion. Devuelve los 12 meses. */
export function estacionalidad(
  items: HistItem[],
  procByCuce: Map<string, HistProceso>,
  campo: 'entrega' | 'publicacion' = 'entrega',
): { mes: number; monto: number; items: number; cantidad: number }[] {
  const acc = Array.from({ length: 12 }, (_, i) => ({ mes: i + 1, monto: 0, items: 0, cantidad: 0 }))
  for (const it of items) {
    const p = procByCuce.get(it.cuce)
    const fecha =
      campo === 'entrega'
        ? it.fecha_entrega ?? p?.fecha_entrega ?? it.fecha_publicacion ?? p?.fecha_publicacion ?? null
        : it.fecha_publicacion ?? p?.fecha_publicacion ?? null
    if (!fecha) continue
    const mes = Number(fecha.slice(5, 7))
    if (!mes || mes < 1 || mes > 12) continue
    const bucket = acc[mes - 1]
    bucket.monto += num(it.monto_total) || num(it.precio_adjudicado) * num(it.cantidad)
    bucket.items += 1
    bucket.cantidad += num(it.cantidad)
  }
  return acc
}

export type BudgetAnual = { anio: number; referencial: number; adjudicado: number; ejecutado: number }

/** Presupuestado vs adjudicado vs ejecutado, por año. */
export function budgetPorAnio(items: HistItem[], procByCuce: Map<string, HistProceso>): BudgetAnual[] {
  const map = new Map<number, BudgetAnual>()
  for (const it of items) {
    const anio = itemAnio(it, procByCuce)
    if (!anio) continue
    const row = map.get(anio) ?? { anio, referencial: 0, adjudicado: 0, ejecutado: 0 }
    const cant = num(it.cantidad)
    row.referencial += num(it.precio_referencial) * cant || 0
    row.adjudicado += num(it.monto_total) || num(it.precio_adjudicado) * cant
    row.ejecutado += num(it.monto_ejecutado)
    map.set(anio, row)
  }
  return Array.from(map.values()).sort((a, b) => a.anio - b.anio)
}

export type Proyeccion = {
  nextAnio: number
  nextValor: number
  slope: number
  r2: number
  base: { anio: number; valor: number }[]
}

/** Regresión lineal simple sobre totales anuales → proyecta el año siguiente.
 *  Requiere ≥2 años con dato. Null si no hay suficiente historia. */
export function proyectarAnual(points: { anio: number; valor: number }[]): Proyeccion | null {
  const pts = points.filter((p) => p.valor > 0)
  if (pts.length < 2) return null
  const n = pts.length
  const sx = pts.reduce((s, p) => s + p.anio, 0)
  const sy = pts.reduce((s, p) => s + p.valor, 0)
  const sxx = pts.reduce((s, p) => s + p.anio * p.anio, 0)
  const sxy = pts.reduce((s, p) => s + p.anio * p.valor, 0)
  const denom = n * sxx - sx * sx
  if (denom === 0) return null
  const slope = (n * sxy - sx * sy) / denom
  const intercept = (sy - slope * sx) / n
  const meanY = sy / n
  let ssRes = 0
  let ssTot = 0
  for (const p of pts) {
    const pred = slope * p.anio + intercept
    ssRes += (p.valor - pred) ** 2
    ssTot += (p.valor - meanY) ** 2
  }
  const r2 = ssTot === 0 ? 1 : Math.max(0, 1 - ssRes / ssTot)
  const nextAnio = Math.max(...pts.map((p) => p.anio)) + 1
  const nextValor = Math.max(0, slope * nextAnio + intercept)
  return { nextAnio, nextValor, slope, r2, base: pts }
}

// ─── Rankings ────────────────────────────────────────────────────────────────

export type Ranking = { label: string; value: number; extra?: number; id?: string }

export function topBy<T>(
  rows: T[],
  keyFn: (r: T) => string | null,
  valFn: (r: T) => number,
  limit = 10,
): { key: string; value: number; count: number }[] {
  const map = new Map<string, { value: number; count: number }>()
  for (const r of rows) {
    const k = keyFn(r)
    if (!k) continue
    const cur = map.get(k) ?? { value: 0, count: 0 }
    cur.value += valFn(r)
    cur.count += 1
    map.set(k, cur)
  }
  return Array.from(map.entries())
    .map(([key, v]) => ({ key, ...v }))
    .sort((a, b) => b.value - a.value)
    .slice(0, limit)
}

// ─── Formato ───────────────────────────────────────────────────────────────

export function fmtMonto(n: number): string {
  if (n >= 1_000_000_000) return `Bs. ${(n / 1_000_000_000).toFixed(1)}B`
  if (n >= 1_000_000) return `Bs. ${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `Bs. ${(n / 1_000).toFixed(0)}K`
  return `Bs. ${Math.round(n).toLocaleString('es-BO')}`
}

export function fmtNum(n: number): string {
  return Math.round(n).toLocaleString('es-BO')
}

// ─── Filtros ───────────────────────────────────────────────────────────────

export type HistFiltros = { entidad?: string; anioDesde?: number | null; anioHasta?: number | null }

export function filtrarItems(
  items: HistItem[],
  procByCuce: Map<string, HistProceso>,
  f: HistFiltros,
): HistItem[] {
  return items.filter((it) => {
    if (f.entidad && it.entidad_codigo !== f.entidad) return false
    if (f.anioDesde != null || f.anioHasta != null) {
      const a = itemAnio(it, procByCuce)
      if (a == null) return false
      if (f.anioDesde != null && a < f.anioDesde) return false
      if (f.anioHasta != null && a > f.anioHasta) return false
    }
    return true
  })
}

export function filtrarProcesos(procesos: HistProceso[], f: HistFiltros): HistProceso[] {
  return procesos.filter((p) => {
    if (f.entidad && p.entidad_codigo !== f.entidad) return false
    if (f.anioDesde != null || f.anioHasta != null) {
      const a = p.cuce_anio ?? yearOf(p.fecha_publicacion)
      if (a == null) return false
      if (f.anioDesde != null && a < f.anioDesde) return false
      if (f.anioHasta != null && a > f.anioHasta) return false
    }
    return true
  })
}

export function procByCuceMap(procesos: HistProceso[]): Map<string, HistProceso> {
  const m = new Map<string, HistProceso>()
  for (const p of procesos) m.set(p.cuce, p)
  return m
}
