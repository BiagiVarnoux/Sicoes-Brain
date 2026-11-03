#!/bin/bash
# ───────────────────────────────────────────────────────────────────────────
# Doble clic para correr el SCRAPER HISTÓRICO (sin escribir nada ni tocar Brave).
# Abre Brave con debugging si hace falta, espera a que esté listo, y corre el
# scraper. El script navega al portal y cierra el popup de comunicados solo.
#
# Editá ENTIDAD / ANIO / N acá abajo para cambiar qué barre.
# ───────────────────────────────────────────────────────────────────────────
ENTIDAD="0660-10"
ANIO="2024"
# N = límite total de procesos. N="0" barre TODO el año (todas las páginas).
N="10"
# REPARSE="1" re-escribe procesos que ya estaban en la base (para corregir/actualizar).
# Dejalo en "0" para corridas normales (salta los ya hechos).
REPARSE="1"

SCRAPER="/Users/fabriziocuellar/Sicoes-Brain/scraper"
PY="$SCRAPER/venv/bin/python"
BRAVE="/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
PERFIL="/tmp/brave-sicoes"
cd "$SCRAPER" || exit 1

echo "════════════════════════════════════"
echo "   SCRAPER HISTÓRICO SICOES"
echo "   Entidad: $ENTIDAD   Año: $ANIO   (N=$N)"
echo "════════════════════════════════════"

# 1) Brave con debugging (reutiliza si ya está abierto)
puerto_ok() { curl -s -m 2 http://localhost:9222/json/version >/dev/null 2>&1; }

if puerto_ok; then
  echo "✓ Brave con debugging ya está abierto."
else
  echo "Abriendo Brave (en este equipo puede tardar un minuto)..."
  "$BRAVE" --remote-debugging-port=9222 --user-data-dir="$PERFIL" >/dev/null 2>&1 &
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

# 2) Scraper histórico (navega, parsea forms, baja DBC, escribe a Supabase)
echo ""; echo ">>> Corriendo scraper histórico..."
echo "    (No uses Brave mientras corre — lo maneja el script.)"
FLAGS=(--entidad "$ENTIDAD" --anio "$ANIO" --n "$N")
[ "$REPARSE" = "1" ] && FLAGS+=(--reparse)
"$PY" historico.py "${FLAGS[@]}" \
  || echo "⚠ el scraper terminó con error."

echo ""
echo "✅ Listo. Datos en Supabase (hist_procesos / hist_items)."
echo "   DBC recortados en: $SCRAPER/salidas/historico_${ENTIDAD}_${ANIO}"
read -r -p "Presioná Enter para cerrar esta ventana..." _
