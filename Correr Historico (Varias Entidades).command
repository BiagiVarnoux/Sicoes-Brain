#!/bin/bash
# ───────────────────────────────────────────────────────────────────────────
# Doble clic para correr el SCRAPER HISTÓRICO sobre VARIAS ENTIDADES en fila.
# Tiene su propio puerto (9225), así que podés correrlo en paralelo con los
# otros dos comandos sin que se pisen.
#
# Te pregunta:
#   · un rango de años POR DEFECTO (compartido por todas las entidades)
#   · luego vas cargando entidades, UNA POR LÍNEA. Cada entidad puede llevar
#     su propio rango pegado con dos puntos, p.ej:
#         0660-06               → usa el rango por defecto
#         0660-12:2022-2026     → sobreescribe el rango SOLO para esa entidad
#         0660-10:2024 2025     → también vale separar años con espacio
#     Enter en blanco para terminar la lista.
#   · si re-procesar lo ya guardado (aplica a todas).
#
# Corre entidad por entidad, y dentro de cada una, año por año. Si una se
# corta, NO se pierde nada: cada proceso se guarda apenas termina, y al volver
# a correr (sin re-procesar) salta los ya hechos y sigue.
# ───────────────────────────────────────────────────────────────────────────
SCRAPER="/Users/fabriziocuellar/Sicoes-Brain/scraper"
PY="$SCRAPER/venv/bin/python"
BRAVE="/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
# Puerto 9225: distinto al Radar (9222) y a los dos históricos (9223/9224).
PUERTO="9225"
PERFIL="/tmp/brave-sicoes-hist-3"
export CDP_URL="http://localhost:$PUERTO"
cd "$SCRAPER" || exit 1

echo "════════════════════════════════════"
echo "   SCRAPER HISTÓRICO SICOES (Varias entidades — puerto $PUERTO)"
echo "════════════════════════════════════"

# 1) Brave con debugging (reutiliza si ya está abierto)
puerto_ok() { curl -s -m 2 "http://localhost:$PUERTO/json/version" >/dev/null 2>&1; }

if puerto_ok; then
  echo "✓ Brave con debugging ya está abierto (puerto $PUERTO)."
else
  echo "Abriendo Brave en puerto $PUERTO (en este equipo puede tardar un minuto)..."
  "$BRAVE" --remote-debugging-port="$PUERTO" --user-data-dir="$PERFIL" >/dev/null 2>&1 &
  printf "Esperando a que Brave esté listo"
  LISTO=0
  for i in $(seq 1 120); do
    if puerto_ok; then LISTO=1; break; fi
    printf "."; sleep 1
  done
  echo ""
  if [ "$LISTO" -ne 1 ]; then
    echo "Brave está tardando más de lo normal."
    read -r -p "Cuando la ventana de Brave YA esté abierta, presioná Enter para seguir..." _
    for i in $(seq 1 40); do puerto_ok && { LISTO=1; break; }; sleep 1; done
  fi
  if [ "$LISTO" -ne 1 ]; then
    echo "✗ No se pudo conectar a Brave con debugging."
    echo "  Probá cerrar Brave del todo y volvé a dar doble clic."
    read -r -p "Enter para cerrar..." _; exit 1
  fi
  echo "✓ Brave listo."
fi

# ── Helper: expande "2022-2024" / "2022 2023" / "2024" a una lista de años ──
#    Imprime los años separados por espacio (vacío si no hay ninguno válido).
expandir_anios() {
  local entrada="$1" out=() tok a b y
  for tok in $entrada; do
    if [[ "$tok" =~ ^([0-9]{4})-([0-9]{4})$ ]]; then
      a="${BASH_REMATCH[1]}"; b="${BASH_REMATCH[2]}"
      if [ "$a" -le "$b" ]; then for ((y=a; y<=b; y++)); do out+=("$y"); done
      else for ((y=a; y>=b; y--)); do out+=("$y"); done; fi
    elif [[ "$tok" =~ ^[0-9]{4}$ ]]; then
      out+=("$tok")
    fi
  done
  echo "${out[*]}"
}

# 2) Rango de años por defecto (compartido)
echo ""
read -r -p "Años POR DEFECTO para todas  ('2022-2024', '2024 2025' o '2024') [2024]: " ANIOS_DEF_IN
ANIOS_DEF_IN="${ANIOS_DEF_IN:-2024}"
ANIOS_DEF="$(expandir_anios "$ANIOS_DEF_IN")"
if [ -z "$ANIOS_DEF" ]; then
  echo "✗ El rango por defecto no tiene años válidos."; read -r -p "Enter para cerrar..." _; exit 1
fi

# 3) Cargar entidades (una por línea; opcional 'codigo:años' para sobreescribir)
echo ""
echo "Cargá las entidades, UNA POR LÍNEA. Enter en blanco para terminar."
echo "  · solo el código           →  usa los años por defecto ($ANIOS_DEF)"
echo "  · codigo:2022-2026         →  rango propio para esa entidad"
echo ""
ENTIDADES=()       # códigos
RANGOS=()          # años expandidos, alineados por índice con ENTIDADES
n=1
while true; do
  read -r -p "  Entidad #$n (Enter para terminar): " LINEA
  [ -z "$LINEA" ] && break
  CODIGO="${LINEA%%:*}"
  CODIGO="${CODIGO// /}"               # sin espacios en el código
  if [[ "$LINEA" == *:* ]]; then
    ANIOS_ENT="$(expandir_anios "${LINEA#*:}")"
  else
    ANIOS_ENT="$ANIOS_DEF"
  fi
  if [ -z "$CODIGO" ]; then
    echo "    (código vacío, ignorado)"; continue
  fi
  if [ -z "$ANIOS_ENT" ]; then
    echo "    (sin años válidos para $CODIGO, uso los por defecto)"; ANIOS_ENT="$ANIOS_DEF"
  fi
  ENTIDADES+=("$CODIGO")
  RANGOS+=("$ANIOS_ENT")
  echo "    + $CODIGO  →  años: $ANIOS_ENT"
  n=$((n+1))
done

if [ "${#ENTIDADES[@]}" -eq 0 ]; then
  echo "✗ No cargaste ninguna entidad."; read -r -p "Enter para cerrar..." _; exit 1
fi

read -r -p "¿Re-procesar lo ya guardado? (s/N): " REP_IN
REPARSE="0"; [[ "$REP_IN" =~ ^[sSyY] ]] && REPARSE="1"

echo ""
echo "────────────────────────────────────"
echo "  Entidades a correr (en orden):"
for i in "${!ENTIDADES[@]}"; do
  echo "    · ${ENTIDADES[$i]}  →  ${RANGOS[$i]}"
done
echo "  Re-procesar: $([ "$REPARSE" = "1" ] && echo "SÍ" || echo "no (continúa donde quedó)")"
echo "────────────────────────────────────"

# 4) Correr: entidad por entidad, y dentro de cada una, año por año.
#    caffeinate -dimsu impide que la Mac duerma mientras corre.
echo ""; echo ">>> Corriendo (la Mac no dormirá mientras corre)..."
echo "    (No uses este Brave mientras corre — lo maneja el script.)"
for i in "${!ENTIDADES[@]}"; do
  ENT="${ENTIDADES[$i]}"
  echo ""
  echo "╔══════════════════════════════════╗"
  echo "   ENTIDAD $ENT  (años: ${RANGOS[$i]})"
  echo "╚══════════════════════════════════╝"
  for ANIO in ${RANGOS[$i]}; do
    echo ""; echo "══════ $ENT · Año $ANIO ══════"
    FLAGS=(--entidad "$ENT" --anio "$ANIO" --n 0)
    [ "$REPARSE" = "1" ] && FLAGS+=(--reparse)
    caffeinate -dimsu "$PY" historico.py "${FLAGS[@]}" \
      || echo "⚠ $ENT año $ANIO terminó con error (lo ya guardado se conserva)."
  done
done

echo ""
echo "✅ Listo con las ${#ENTIDADES[@]} entidades. Datos en Supabase (hist_procesos / hist_items)."
read -r -p "Presioná Enter para cerrar esta ventana..." _
