#!/bin/bash
# Variante del lanzador histórico: entidad + gestión, originales y Markdown locales.
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
if [ "${1:-}" = --check ]; then exec "$PY" -B -m scraper.historico_local --check; fi
echo 'SICOES LOCAL — histórico documental por entidad y gestión'
if [ "$#" -gt 0 ]; then echo 'Solo se admite --check'; exit 2; fi
echo 'Sin límite de procesos: Bienes, estado 2C; CM, ANPE, ANPP y LP.'
echo 'Brave histórico local: puerto 9226. Resuelve manualmente comunicados/captcha.'
read -r -p 'Código de entidad [0660-10]: ' entity
read -r -p "Año(s): uno '2024', varios '2022 2023 2024' o rango '2022-2024' [2024]: " years_input
entity="${entity:-0660-10}";years_input="${years_input:-2024}"
years=()
for token in $years_input; do
  if [[ "$token" =~ ^([0-9]{4})-([0-9]{4})$ ]]; then
    first=$((10#${BASH_REMATCH[1]}));last=$((10#${BASH_REMATCH[2]}))
    if [ "$first" -lt 2000 ] || [ "$first" -gt 2100 ] || [ "$last" -lt 2000 ] || [ "$last" -gt 2100 ]; then
      echo "Rango fuera de 2000–2100: $token";exit 2
    fi
    if [ "$first" -le "$last" ]; then
      for ((y=first;y<=last;y++)); do years+=("$y"); done
    else
      for ((y=first;y>=last;y--)); do years+=("$y"); done
    fi
  elif [[ "$token" =~ ^[0-9]{4}$ ]] && [ "$token" -ge 2000 ] && [ "$token" -le 2100 ]; then
    years+=("$token")
  else
    echo "Año o rango inválido: $token";exit 2
  fi
done
if [ "${#years[@]}" -eq 0 ]; then echo 'No se indicaron años válidos';exit 2;fi
mkdir -p "$ROOT/scraper/historico_local/data/historico_http_paginas_logs"
log="$ROOT/scraper/historico_local/data/historico_http_paginas_logs/$(date -u +%Y%m%dT%H%M%SZ)_$$.log"
echo "Entidad $entity — gestiones ${years[*]}. Log: $log"
result=0
seen=" "
for year in "${years[@]}"; do
  case "$seen" in *" $year "*) continue;; esac
  seen="$seen$year "
  echo "══════ Gestión $year ══════"
  if command -v caffeinate >/dev/null 2>&1; then
    caffeinate -dimsu "$PY" -B -m scraper.historico_local --entidad "$entity" --anio "$year" 2>&1 | tee -a "$log"
    run_exit=${PIPESTATUS[0]}
  else
    "$PY" -B -m scraper.historico_local --entidad "$entity" --anio "$year" 2>&1 | tee -a "$log"
    run_exit=${PIPESTATUS[0]}
  fi
  if [ "$run_exit" -eq 130 ]; then exit 130;fi
  if [ "$run_exit" -ne 0 ]; then
    result="$run_exit"
    echo "Gestión $year terminó con código $run_exit; sus archivos se conservan."
  fi
done
exit "$result"
