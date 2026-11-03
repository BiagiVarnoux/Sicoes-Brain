-- ─────────────────────────────────────────────────────────────────────────────
-- MODO HISTÓRICO POR ENTIDAD (análisis de qué solicita una entidad en el tiempo)
-- Independiente del radar y del scraper de `procesos`/`items`. No toca esas tablas.
--
-- Fuentes (confirmadas en la prueba de la entidad 0660-10, año 2024):
--   · Backbone determinista (TODAS las modalidades), parseado de los formularios:
--       FORM100/FORM110 → ítems REQUERIDOS (UNSPSC, desc, unidad, cant, precio ref)
--       FORM200/FORM220 → ítems ADJUDICADOS (precio adjudicado + proveedor)
--       FORM500         → recepción/ejecución (fechas de entrega)
--   · Enriquecimiento con IA (solo ANPE/ANPP/LP, que sí traen DBC .docx):
--       DBC recortado a "Especificaciones Técnicas" + "Precio Referencial"
--         → specs finas por ítem
-- Modalidades incluidas: CM, ANPE, ANPP, LP  (se excluye CND1 y otras).
--
-- Orden de creación (por la FK de hist_items): canónicos → procesos → ítems.
-- ─────────────────────────────────────────────────────────────────────────────

-- Catálogo de "bienes canónicos". Lo llena la PASADA GLOBAL de agrupación por IA
-- al final de todo el scrapeo (agrupa variantes del mismo bien aunque difieran el
-- título, la descripción o el UNSPSC). Re-ejecutable.
create table if not exists public.hist_productos_canonicos (
  id             bigint generated always as identity primary key,
  nombre_canonico text not null,      -- etiqueta legible, ej. "Tóner HP CE278A (78A)"
  categoria      text,                -- agrupación amplia, ej. "Tóner / cartucho"
  unspsc_codigo  text,                -- el UNSPSC más frecuente del grupo (referencia)
  n_items        integer default 0,   -- cuántos hist_items agrupa (se recalcula)
  creado_en      timestamptz default now(),
  actualizado_en timestamptz default now()
);
create index if not exists idx_hist_canon_cat on public.hist_productos_canonicos (categoria);

-- Un renglón por proceso (CUCE).
create table if not exists public.hist_procesos (
  cuce                text primary key,
  entidad_codigo      text not null,              -- ej. 0660-10
  entidad_nombre      text,
  modalidad           text,                        -- CM / ANPE / ANPP / LP
  objeto              text,
  tipo_contratacion   text,                        -- Bienes
  estado              text,                        -- Contratado / Adjudicado
  fecha_publicacion   date,
  fecha_presentacion  date,
  cuce_anio           integer,                     -- para agrupar series por año
  monto_adjudicado    numeric,                     -- suma de los ítems adjudicados
  fecha_firma_contrato date,                        -- FORM500: firma de contrato (mín del proceso)
  fecha_entrega        date,                         -- FORM500: recepción definitiva (máx del proceso)
  tiene_dbc           boolean default false,
  forms_capturados    text[]  default '{}',        -- ej. {FORM110,FORM220,FORM500}
  creado_en           timestamptz default now(),
  actualizado_en      timestamptz default now()
);
create index if not exists idx_hist_proc_entidad on public.hist_procesos (entidad_codigo);
create index if not exists idx_hist_proc_fecha   on public.hist_procesos (fecha_publicacion desc);
create index if not exists idx_hist_proc_anio    on public.hist_procesos (cuce_anio);

-- Un renglón por ítem solicitado dentro de un proceso.
create table if not exists public.hist_items (
  id                   bigint generated always as identity primary key,
  cuce                 text not null references public.hist_procesos(cuce) on delete cascade,
  nro_item             integer,
  lote                 text,        -- si el proceso agrupa por lote (típico en LP)
  unspsc_codigo        text,
  descripcion          text,        -- del formulario (requerimiento de la entidad)
  especificaciones     text,        -- specs finas del DBC (NULL si no hay DBC, p.ej. CM)
  unidad_medida        text,
  cantidad             numeric,
  moneda               text default 'BOB',  -- casi siempre bolivianos; defensivo
  precio_referencial   numeric,     -- lo que la entidad pide pagar (DBC / FORM110 preseleccionado)
  precio_adjudicado    numeric,     -- precio real (FORM200/220)
  monto_total          numeric,
  proveedor            text,        -- adjudicado (FORM200/220)
  estado_recepcion     text,        -- FORM500: 'Recibido' / etc.
  cantidad_recibida    numeric,     -- FORM500: cantidad recepcionada
  monto_ejecutado      numeric,     -- FORM500: monto real ejecutado (puede diferir del adjudicado)
  fecha_entrega        date,        -- FORM500: fecha de recepción definitiva del ítem
  fecha_publicacion    date,        -- desnormalizado del proceso (para series de tiempo)
  entidad_codigo       text,        -- desnormalizado (para filtrar sin join)
  modalidad            text,        -- desnormalizado
  fuente               text,        -- de dónde salió: form110 / form220 / dbc ...
  producto_canonico_id bigint references public.hist_productos_canonicos(id) on delete set null,
  creado_en            timestamptz default now()
);
create index if not exists idx_hist_item_cuce     on public.hist_items (cuce);
create index if not exists idx_hist_item_canonico on public.hist_items (producto_canonico_id);
create index if not exists idx_hist_item_unspsc   on public.hist_items (unspsc_codigo);
create index if not exists idx_hist_item_entidad  on public.hist_items (entidad_codigo);

-- RLS: mismo patrón que el resto del proyecto (lectura pública para el dashboard;
-- escritura del scraper vía la API key del .env).
alter table public.hist_productos_canonicos enable row level security;
alter table public.hist_procesos            enable row level security;
alter table public.hist_items               enable row level security;

create policy "public_read_hist_canon" on public.hist_productos_canonicos for select to anon using (true);
create policy "public_read_hist_proc"  on public.hist_procesos            for select to anon using (true);
create policy "public_read_hist_item"  on public.hist_items               for select to anon using (true);
