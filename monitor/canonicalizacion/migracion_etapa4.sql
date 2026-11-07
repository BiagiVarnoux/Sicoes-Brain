-- ETAPA 4 — MIGRACIÓN DE ESQUEMA (BORRADOR, NO APLICADA).
-- Habilita el árbol canónico reversible con log de eventos append-only.
-- NO se ejecuta hasta aprobación explícita. Idempotente (if not exists / add column if not exists).

-- 1) Árbol canónico: nivel + jerarquía + atributos + exemplar + versión + confianza.
alter table public.hist_productos_canonicos
  add column if not exists nivel            text,     -- familia_amplia | subfamilia | producto
  add column if not exists parent_id        bigint references public.hist_productos_canonicos(id) on delete set null,
  add column if not exists atributos        jsonb,    -- atributos canónicos (del exemplar)
  add column if not exists exemplar_item_id bigint references public.hist_items(id) on delete set null,
  add column if not exists metodo           text,     -- clique_auto | asistido | manual
  add column if not exists confianza        text,     -- confirmado | asistido | candidato
  add column if not exists corrida_version  text;     -- id de la corrida que creó el nodo

create index if not exists idx_hist_canon_parent on public.hist_productos_canonicos (parent_id);
create index if not exists idx_hist_canon_nivel  on public.hist_productos_canonicos (nivel);

-- 2) Log de EVENTOS append-only. No se actualiza ni borra: el estado vigente se reconstruye plegando.
create table if not exists public.hist_canonico_eventos (
  id                        bigint generated always as identity primary key,
  item_id                   bigint not null references public.hist_items(id) on delete cascade,
  tipo_evento               text not null check (tipo_evento in ('ASIGNACION','REVOCACION','SUSTITUCION')),
  producto_canonico_id      bigint references public.hist_productos_canonicos(id) on delete set null, -- destino
  producto_canonico_anterior bigint references public.hist_productos_canonicos(id) on delete set null,
  veredicto_origen          text,     -- SI (clique) | asistido | manual
  razon                     text,
  corrida_version           text not null,
  decidido_por              text not null default 'auto',  -- auto | humano
  creado_en                 timestamptz not null default now()
);
create index if not exists idx_canon_ev_item on public.hist_canonico_eventos (item_id, creado_en desc);
create index if not exists idx_canon_ev_corrida on public.hist_canonico_eventos (corrida_version);

-- 3) Vista de estado VIGENTE: último evento por ítem (producto actual, o NULL si revocado).
create or replace view public.hist_canonico_vigente as
select distinct on (e.item_id)
       e.item_id,
       case when e.tipo_evento = 'REVOCACION' then null else e.producto_canonico_id end as producto_canonico_id,
       e.corrida_version, e.creado_en
from public.hist_canonico_eventos e
order by e.item_id, e.creado_en desc, e.id desc;

-- hist_items.producto_canonico_id queda como CACHÉ derivado de la vista (lo refresca la aplicación de
-- un corte; nunca se edita a mano). RLS igual que el resto (lectura pública; escritura vía service key).
alter table public.hist_canonico_eventos enable row level security;
create policy if not exists "public_read_canon_ev" on public.hist_canonico_eventos for select to anon using (true);
