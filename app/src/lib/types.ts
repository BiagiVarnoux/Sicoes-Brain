export type Proceso = {
  cuce: string
  entidad_codigo: string | null
  entidad_nombre: string | null
  objeto: string
  modalidad: string | null
  estado: string | null
  fecha_publicacion: string | null
  fecha_presentacion: string | null
  monto_referencial: number | null
  monto_adjudicado: number | null
  tipo_contratacion: string | null
}

export type ConvocatoriaRadar = {
  cuce: string
  entidad: string | null
  objeto: string | null
  modalidad: string | null
  tipo_contratacion: string | null
  fecha_publicacion: string | null
  fecha_presentacion: string | null
  fecha_presentacion_raw: string | null
  estado: string | null
  match_dicc: boolean
  match_dicc_terminos: string[] | null
  match_ia: boolean
  match_ia_razon: string | null
  relevante: boolean
  archivos: { nombre: string; token: string }[] | null
  dbc_path: string | null
  dbc_descargado: boolean
  visto: boolean
  descartado: boolean
  creado_en: string
}

export type Entidad = {
  codigo: string
  nombre: string
  departamento: string | null
}

export type SearchParams = {
  q?: string
  modalidad?: string
  estado?: string
  entidad?: string
  page?: string
}

export const MODALIDADES = [
  { value: 'CM', label: 'CM – Contratación Menor' },
  { value: 'ANPE', label: 'ANPE – Hasta Bs 200k' },
  { value: 'ANPP', label: 'ANPP – Mayor Bs 200k' },
  { value: 'CNC', label: 'CNC – Compra Nacional por Convocatoria' },
  { value: 'CND1', label: 'CND1 – Compra Nacional Directa' },
  { value: 'LP', label: 'LP – Licitación Pública' },
  { value: 'CD', label: 'CD – Contratación Directa' },
  { value: 'EX', label: 'EX – Excepción' },
  { value: 'OF', label: 'OF – Otras Formas' },
]

export const ESTADOS = [
  'Contratado',
  'Desierto',
  'Desierto Parcial',
  'Anulado desde la convocatoria',
  'Cancelado',
  'En curso',
  'Adjudicado',
  'Vigente',
  'Suspendido',
]

export const PAGE_SIZE = 25
