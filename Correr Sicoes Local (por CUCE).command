#!/bin/bash
# Variante por CUCE del lanzador histórico local: captura/re-captura procesos
# puntuales (uno o varios), posiblemente de distintas entidades/gestiones, y
# los guarda en la MISMA carpeta que "Correr Sicoes Local.command"
# (scraper/historico_local/data/historico_http_paginas_<entidad>_<gestion>/<CUCE>/).
#
# Pegá los CUCE separados por espacio. Formas aceptadas:
#   · completo:  22-0660-10-1199042-1-2   (se autodescribe: entidad y gestión salen del CUCE)
#   · corto:     1199042                  (convocatoria sola => -1-1; usa Entidad/Gestión)
#   · corto:     1199042-1-2              (par final explícito; usa Entidad/Gestión)
# Si solo usás formas completas, dejá Entidad/Gestión en blanco.
set -u
set -o pipefail
trap 'exit 130' INT TERM
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT" || exit 1
export PYTHONDONTWRITEBYTECODE=1
PY="${SICOES_LOCAL_PYTHON:-}"
if [ -z "$PY" ]; then
  for candidate in "$ROOT/scraper/historico_local/.venv/bin/python" "$ROOT/scraper/venv/bin/python"; do
    if [ -x "$candidate" ]; then PY="$candidate"; break; fi
  done
fi
if [ -z "$PY" ]; then echo 'No se encontró entorno virtual'; exit 1; fi

echo 'SICOES LOCAL — captura/re-captura por CUCE'
echo 'Brave histórico local: puerto 9226. Resuelve manualmente comunicados/captcha.'
echo 'Se guarda en la misma carpeta que el lanzador por entidad/gestión.'
read -r -p 'CUCE(s) separados por espacio: ' cuces_input
if [ -z "${cuces_input// /}" ]; then echo 'No se indicó ningún CUCE'; exit 2; fi
read -r -p 'Entidad (solo si usás formas cortas, p.ej. 0660-10) [vacío]: ' entity
read -r -p 'Gestión (solo si usás formas cortas, p.ej. 2022) [vacío]: ' year

# Partir la línea en tokens.
read -r -a cuces <<< "$cuces_input"

# Flags opcionales de contexto para formas cortas.
scope_flags=()
[ -n "${entity// /}" ] && scope_flags+=(--entidad "$entity")
[ -n "${year// /}" ] && scope_flags+=(--anio "$year")

mkdir -p "$ROOT/scraper/historico_local/data/historico_http_paginas_logs"
log="$ROOT/scraper/historico_local/data/historico_http_paginas_logs/$(date -u +%Y%m%dT%H%M%SZ)_$$_porcuce.log"
echo "CUCE(s): ${cuces[*]}. Log: $log"

if command -v caffeinate >/dev/null 2>&1; then
  caffeinate -dimsu "$PY" -B -m scraper.historico_local.por_cuce "${cuces[@]}" "${scope_flags[@]}" 2>&1 | tee -a "$log"
  run_exit=${PIPESTATUS[0]}
else
  "$PY" -B -m scraper.historico_local.por_cuce "${cuces[@]}" "${scope_flags[@]}" 2>&1 | tee -a "$log"
  run_exit=${PIPESTATUS[0]}
fi
if [ "$run_exit" -eq 130 ]; then exit 130; fi
if [ "$run_exit" -ne 0 ]; then
  echo "Terminó con código $run_exit; lo ya descargado se conserva."
fi
exit "$run_exit"
