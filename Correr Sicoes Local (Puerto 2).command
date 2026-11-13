#!/bin/bash
# ───────────────────────────────────────────────────────────────────────────
# SICOES LOCAL (PUERTO 2) — igual que "Correr Sicoes Local.command" pero en el
# puerto 9227, con su propio perfil de Brave, para correr una SEGUNDA corrida
# EN PARALELO con la primera sin que se pisen.
#
# Importante: usá entidades DISTINTAS a las de la otra corrida. Dos corridas
# sobre la MISMA entidad+año escriben en la misma carpeta y sí chocarían.
#
# Corre UNA O MÁS entidades en fila; dentro de cada una, año por año.
# Te pregunta un rango de años por defecto y luego las entidades, una por
# línea (opcional 'codigo:2022-2026' para un rango propio). Enter en blanco
# para terminar. Si se corta, no se pierde nada: al reanudar salta lo hecho.
# ───────────────────────────────────────────────────────────────────────────
set -u
set -o pipefail
trap 'exit 130' INT TERM
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT" || exit 1
export PYTHONDONTWRITEBYTECODE=1
# Puerto 9227: propio de esta 2ª corrida (la primera usa 9226).
export SICOES_LOCAL_CDP_PORT="${SICOES_LOCAL_CDP_PORT:-9227}"

# Mantener la Mac despierta TODA la corrida (esta máquina tiende a dormirse).
# Atado a la vida de este script (-w "$$"): cubre prompts, arranque de Brave y
# los huecos entre años/entidades, no solo cada proceso de Python.
if command -v caffeinate >/dev/null 2>&1; then caffeinate -dimsu -w "$$" & fi

PY="${SICOES_LOCAL_PYTHON:-}"
if [ -z "$PY" ]; then
  for candidate in "$ROOT/scraper/historico_local/.venv/bin/python" "$ROOT/scraper/venv/bin/python"; do
    if [ -x "$candidate" ]; then PY="$candidate"; break; fi
  done
fi
if [ -z "$PY" ]; then echo 'No se encontró entorno virtual'; exit 1; fi
if [ "${1:-}" = --check ]; then exec "$PY" -B -m scraper.historico_local --check; fi
if [ "$#" -gt 0 ]; then echo 'Solo se admite --check'; exit 2; fi

echo "SICOES LOCAL (PUERTO 2 — paralelo) por entidad y gestión (puerto $SICOES_LOCAL_CDP_PORT)"
echo 'Sin límite de procesos: Bienes, estado 2C; CM, ANPE, ANPP y LP.'
echo "Brave histórico local: puerto $SICOES_LOCAL_CDP_PORT. Resuelve manualmente comunicados/captcha."

# Expande "2022-2024" / "2022 2023" / "2024" (valida 2000–2100).
# Imprime los años separados por espacio (vacío si ninguno es válido).
expandir_anios() {
  local entrada="$1" tok a b y acc=""
  for tok in $entrada; do
    if [[ "$tok" =~ ^([0-9]{4})-([0-9]{4})$ ]]; then
      a=$((10#${BASH_REMATCH[1]})); b=$((10#${BASH_REMATCH[2]}))
      if [ "$a" -lt 2000 ] || [ "$a" -gt 2100 ] || [ "$b" -lt 2000 ] || [ "$b" -gt 2100 ]; then continue; fi
      if [ "$a" -le "$b" ]; then y=$a; while [ "$y" -le "$b" ]; do acc="$acc $y"; y=$((y+1)); done
      else y=$a; while [ "$y" -ge "$b" ]; do acc="$acc $y"; y=$((y-1)); done; fi
    elif [[ "$tok" =~ ^[0-9]{4}$ ]] && [ "$tok" -ge 2000 ] && [ "$tok" -le 2100 ]; then
      acc="$acc $tok"
    fi
  done
  echo $acc
}

echo ''
read -r -p "Años POR DEFECTO para todas  ('2022-2024', '2024 2025' o '2024') [2024]: " ANIOS_DEF_IN
ANIOS_DEF_IN="${ANIOS_DEF_IN:-2024}"
ANIOS_DEF="$(expandir_anios "$ANIOS_DEF_IN")"
if [ -z "$ANIOS_DEF" ]; then echo 'El rango por defecto no tiene años válidos (2000–2100).'; exit 2; fi

echo ''
echo 'Cargá las entidades, UNA POR LÍNEA. Enter en blanco para terminar.'
echo "  · solo el código        →  usa los años por defecto ($ANIOS_DEF)"
echo '  · codigo:2022-2026      →  rango propio para esa entidad'
echo ''
ENTIDADES=()
RANGOS=()
n=1
while true; do
  read -r -p "  Entidad #$n (Enter para terminar): " LINEA || break
  [ -z "$LINEA" ] && break
  CODIGO="${LINEA%%:*}"; CODIGO="${CODIGO// /}"
  if [[ "$LINEA" == *:* ]]; then ANIOS_ENT="$(expandir_anios "${LINEA#*:}")"; else ANIOS_ENT="$ANIOS_DEF"; fi
  if [ -z "$CODIGO" ]; then echo '    (código vacío, ignorado)'; continue; fi
  if [[ ! "$CODIGO" =~ ^[0-9]{4}-[0-9]{2}$ ]]; then echo "    (código inválido '$CODIGO', ignorado; formato 0000-00)"; continue; fi
  if [ -z "$ANIOS_ENT" ]; then echo "    (sin años válidos para $CODIGO, uso los por defecto)"; ANIOS_ENT="$ANIOS_DEF"; fi
  ENTIDADES+=("$CODIGO"); RANGOS+=("$ANIOS_ENT")
  echo "    + $CODIGO  →  años:$ANIOS_ENT"
  n=$((n+1))
done

if [ "${#ENTIDADES[@]}" -eq 0 ]; then echo 'No cargaste ninguna entidad.'; exit 2; fi

echo ''
echo '────────────────────────────────────'
echo '  Entidades a correr (en orden):'
for i in "${!ENTIDADES[@]}"; do echo "    · ${ENTIDADES[$i]}  →  años:${RANGOS[$i]}"; done
echo '────────────────────────────────────'

mkdir -p "$ROOT/scraper/historico_local/data/historico_http_paginas_logs"
log="$ROOT/scraper/historico_local/data/historico_http_paginas_logs/$(date -u +%Y%m%dT%H%M%SZ)_$$_p2.log"
echo "Log: $log"
result=0
for i in "${!ENTIDADES[@]}"; do
  ENT="${ENTIDADES[$i]}"
  echo ''
  echo '╔══════════════════════════════════╗'
  echo "   ENTIDAD $ENT  (años:${RANGOS[$i]})"
  echo '╚══════════════════════════════════╝'
  seen=" "
  for year in ${RANGOS[$i]}; do
    case "$seen" in *" $year "*) continue;; esac
    seen="$seen$year "
    echo "══════ Gestión $year ══════"
    "$PY" -B -m scraper.historico_local --entidad "$ENT" --anio "$year" 2>&1 | tee -a "$log"
    run_exit=${PIPESTATUS[0]}
    if [ "$run_exit" -eq 130 ]; then exit 130; fi
    if [ "$run_exit" -ne 0 ]; then
      result="$run_exit"
      echo "$ENT · Gestión $year terminó con código $run_exit; sus archivos se conservan."
    fi
  done
done

echo ''
echo "Listo con ${#ENTIDADES[@]} entidad(es)."
exit "$result"
