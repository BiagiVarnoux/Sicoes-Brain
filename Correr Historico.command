#!/bin/bash
# ───────────────────────────────────────────────────────────────────────────
# Doble clic para correr el SCRAPER HISTÓRICO.
# Abre Brave con debugging si hace falta y luego TE PREGUNTA:
#   · el código de la entidad (ej. 0660-10)
#   · el/los año(s): uno ("2024"), varios ("2022 2023 2024") o rango ("2022-2024")
#   · si re-procesar lo ya guardado
# Si se corta a mitad, NO se pierde nada: cada proceso se guarda apenas se
# termina, y al volver a correr (sin re-procesar) salta los ya hechos y sigue.
# ───────────────────────────────────────────────────────────────────────────
SCRAPER="/Users/fabriziocuellar/Sicoes-Brain/scraper"
PY="$SCRAPER/venv/bin/python"
BRAVE="/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
# Puerto y perfil de Brave. Para una 2ª corrida en paralelo, usar el comando
# "Correr Historico (Puerto 2).command" (puerto 9223, perfil aparte).
PUERTO="${PUERTO:-9222}"
PERFIL="${PERFIL:-/tmp/brave-sicoes}"
export CDP_URL="http://localhost:$PUERTO"
cd "$SCRAPER" || exit 1

echo "════════════════════════════════════"
echo "   SCRAPER HISTÓRICO SICOES"
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

# 2) Preguntar qué barrer
echo ""
read -r -p "Código de la entidad [0660-10]: " ENTIDAD
ENTIDAD="${ENTIDAD:-0660-10}"

read -r -p "Año(s)  (uno '2024', varios '2022 2023 2024' o rango '2022-2024') [2024]: " ANIOS_IN
ANIOS_IN="${ANIOS_IN:-2024}"

# Expandir rangos tipo 2022-2024 y armar la lista final de años.
ANIOS=()
for tok in $ANIOS_IN; do
  if [[ "$tok" =~ ^([0-9]{4})-([0-9]{4})$ ]]; then
    a="${BASH_REMATCH[1]}"; b="${BASH_REMATCH[2]}"
    if [ "$a" -le "$b" ]; then for ((y=a; y<=b; y++)); do ANIOS+=("$y"); done
    else for ((y=a; y>=b; y--)); do ANIOS+=("$y"); done; fi
  elif [[ "$tok" =~ ^[0-9]{4}$ ]]; then
    ANIOS+=("$tok")
  else
    echo "  (ignorando '$tok': no es un año ni un rango válido)"
  fi
done
if [ "${#ANIOS[@]}" -eq 0 ]; then
  echo "✗ No diste ningún año válido."; read -r -p "Enter para cerrar..." _; exit 1
fi

read -r -p "¿Re-procesar lo ya guardado? (s/N): " REP_IN
REPARSE="0"; [[ "$REP_IN" =~ ^[sSyY] ]] && REPARSE="1"

echo ""
echo "────────────────────────────────────"
echo "  Entidad:  $ENTIDAD"
echo "  Años:     ${ANIOS[*]}"
echo "  Re-procesar: $([ "$REPARSE" = "1" ] && echo "SÍ" || echo "no (continúa donde quedó)")"
echo "────────────────────────────────────"

# 3) Correr el scraper una vez por año (histórico.py toma un año por corrida).
#    caffeinate -dimsu impide que la Mac entre en reposo mientras corre, así
#    podés bloquear la pantalla sin cortar la corrida.
echo ""; echo ">>> Corriendo scraper histórico (la Mac no dormirá mientras corre)..."
echo "    (No uses Brave mientras corre — lo maneja el script.)"
for ANIO in "${ANIOS[@]}"; do
  echo ""; echo "══════ Año $ANIO ══════"
  FLAGS=(--entidad "$ENTIDAD" --anio "$ANIO" --n 0)
  [ "$REPARSE" = "1" ] && FLAGS+=(--reparse)
  caffeinate -dimsu "$PY" historico.py "${FLAGS[@]}" \
    || echo "⚠ el año $ANIO terminó con error (lo ya guardado se conserva)."
done

echo ""
echo "✅ Listo. Datos en Supabase (hist_procesos / hist_items)."
echo "   DBC recortados en: $SCRAPER/salidas/historico_${ENTIDAD}_<año>"
read -r -p "Presioná Enter para cerrar esta ventana..." _
