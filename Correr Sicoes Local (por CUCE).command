#!/bin/bash
# Variante por CUCE del lanzador histórico local: captura/re-captura procesos
# puntuales buscando por NÚMERO DE CONVOCATORIA (no hace falta entidad ni año).
# Guarda en la MISMA carpeta que "Correr Sicoes Local.command"
# (scraper/historico_local/data/historico_http_paginas_<entidad>_<gestion>/<CUCE>/).
#
# Pegá uno o más, separados por espacio o coma. Formas aceptadas:
#   · 1199042                  → convocatoria sola (variante -1-1 por defecto)
#   · 1199042-1-2              → variante explícita (p.ej. -1-2 o -2-1)
#   · 22-0660-10-1199042-1-2   → CUCE completo (solo se usa 1199042-1-2)
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

echo 'SICOES LOCAL — captura/re-captura por nº de convocatoria'
echo 'Brave histórico local: puerto 9226. Resuelve manualmente comunicados/captcha.'
echo 'Se guarda en la misma carpeta que el lanzador por entidad/gestión.'
read -r -p 'Convocatoria(s) (ej: 1199042-1-2 1333011): ' cuces_input
if [ -z "${cuces_input// /}" ]; then echo 'No se indicó ninguna convocatoria'; exit 2; fi

# Partir la línea en tokens (tolera comas y/o espacios como separador).
cuces_input="${cuces_input//,/ }"
read -r -a cuces <<< "$cuces_input"

mkdir -p "$ROOT/scraper/historico_local/data/historico_http_paginas_logs"
log="$ROOT/scraper/historico_local/data/historico_http_paginas_logs/$(date -u +%Y%m%dT%H%M%SZ)_$$_porcuce.log"
echo "Convocatoria(s): ${cuces[*]}. Log: $log"

if command -v caffeinate >/dev/null 2>&1; then
  caffeinate -dimsu "$PY" -B -m scraper.historico_local.por_cuce "${cuces[@]}" 2>&1 | tee -a "$log"
  run_exit=${PIPESTATUS[0]}
else
  "$PY" -B -m scraper.historico_local.por_cuce "${cuces[@]}" 2>&1 | tee -a "$log"
  run_exit=${PIPESTATUS[0]}
fi
if [ "$run_exit" -eq 130 ]; then exit 130; fi
if [ "$run_exit" -ne 0 ]; then
  echo "Terminó con código $run_exit; lo ya descargado se conserva."
fi
exit "$run_exit"
