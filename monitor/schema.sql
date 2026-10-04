-- Tabla del radar de convocatorias (Supabase proyecto Sicoes Brain).
-- Aplicada vía migración `crear_convocatorias_radar` el 2026-10-03.
-- Independiente de procesos/items; no tocar esas tablas.

create table if not exists public.convocatorias_radar (
  cuce                   text primary key,
  entidad                text,
  objeto                 text,
  modalidad              text,          -- codigo: CM / LP / ANPE / ANPP
  tipo_contratacion      text,          -- Bienes, Obras, etc.
  departamento           text,
  monto                  numeric,
  fecha_publicacion      date,
  fecha_presentacion     date,
  fecha_presentacion_raw text,
  estado                 text,

  -- doble filtro
  match_dicc             boolean default false,
  match_dicc_terminos    text[]  default '{}',
  match_ia               boolean default false,
  match_ia_razon         text,
  relevante              boolean default false,   -- OR de los dos filtros

  -- archivos / DBC
  archivos               jsonb   default '[]'::jsonb,  -- [{nombre, token}] (tokens SICOES)
  dbc_archivos           jsonb   default '[]'::jsonb,  -- [{nombre, url}] subidos a Storage
  dbc_path               text,
  dbc_descargado         boolean default false,

  -- gestion del usuario en el dashboard
  visto                  boolean default false,
  descartado             boolean default false,
  motivo_descarte        text[]  default '{}',   -- producto/precio/especificaciones/garantias/marca/plazos/otro
  nota_descarte          text,                   -- nota libre (ej. "no hago impresoras 3D")
  descartado_en          timestamptz,            -- solo 'producto' entrena los filtros

  creado_en              timestamptz default now(),
  actualizado_en         timestamptz default now()
);

create index if not exists idx_radar_fecha_pub  on public.convocatorias_radar (fecha_publicacion desc);
create index if not exists idx_radar_fecha_pres on public.convocatorias_radar (fecha_presentacion);
create index if not exists idx_radar_relevante  on public.convocatorias_radar (relevante) where relevante = true;

alter table public.convocatorias_radar enable row level security;

create policy "public_read_radar"   on public.convocatorias_radar for select to anon using (true);
create policy "public_update_radar" on public.convocatorias_radar for update to anon using (true) with check (true);

-- ─────────────────────────────────────────────────────────────────────────────
-- Espejo (solo lectura) del historial del ERP "Contabilidad", para enriquecer el
-- radar y entrenar la IA. numero_sicoes == cuce4 del radar. Lo puebla erp_sync.py.
-- Solo campos NO sensibles (sin costos/piso/margen).
create table if not exists public.erp_licitaciones (
  numero_sicoes      text primary key,            -- = cuce4 del radar
  nombre             text,
  entidad            text,
  tipo_proceso       text,
  estado             text,                          -- ADJUDICADA/PERDIDA/ENTREGADA/COBRADA/DESIERTA/...
  ganada             boolean,                        -- estado in (ADJUDICADA,ENTREGADA,COBRADA)
  fecha_presentacion date,
  sincronizado_en    timestamptz default now()
);
create table if not exists public.erp_productos (
  id             bigint generated always as identity primary key,
  numero_sicoes  text not null references public.erp_licitaciones(numero_sicoes) on delete cascade,
  orden          integer,
  nombre         text,     -- producto + modelo (texto libre del ERP)
  especificacion text,     -- specs cumplidas
  cantidad       numeric,
  precio_entidad numeric,  -- referencia de la entidad
  precio_ofertado numeric  -- a cuánto se ofertó
);
create index if not exists idx_erp_prod_sicoes on public.erp_productos(numero_sicoes);
alter table public.erp_licitaciones enable row level security;
alter table public.erp_productos    enable row level security;
create policy "public_read_erp_lic"  on public.erp_licitaciones for select to anon using (true);
create policy "public_read_erp_prod" on public.erp_productos    for select to anon using (true);

-- Caché del parseo del Formulario C-1 (una vez por documento). Lo puebla c1_parse.py.
create table if not exists public.erp_c1 (
  id             bigint generated always as identity primary key,
  numero_sicoes  text not null,             -- = cuce4
  doc_nombre     text,
  doc_path       text unique not null,
  items          jsonb default '[]'::jsonb, -- [{item,requerimiento_entidad,ofertado,marca,modelo,especificaciones,cantidad,precio_unitario}]
  texto_crudo    text,
  metodo         text,                       -- 'texto' | 'ocr_pendiente'
  parseado_en    timestamptz default now()
);
create index if not exists idx_erp_c1_sicoes on public.erp_c1(numero_sicoes);
alter table public.erp_c1 enable row level security;
create policy "public_read_erp_c1" on public.erp_c1 for select to anon using (true);
