#!/bin/bash
# ───────────────────────────────────────────────────────────────────────────
# Doble clic para correr el Radar (sin escribir nada en la terminal).
# Abre Brave con debugging (si no está), y corre:
#   radar.py --auto  →  dbc_specs.py
# (El historial del ERP se sincroniza aparte con erp_sync.py cuando quieras.)
# ───────────────────────────────────────────────────────────────────────────
MONITOR="/Users/fabriziocuellar/Sicoes-Brain/monitor"
PY="/Users/fabriziocuellar/Sicoes-Brain/scraper/venv/bin/python"
BRAVE="/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
PERFIL="/tmp/brave-sicoes"
cd "$MONITOR" || exit 1

echo "════════════════════════════════════"
echo "   RADAR SICOES — corrida completa"
echo "════════════════════════════════════"

# 1) Brave con debugging (reutiliza si ya está abierto)
if curl -s -m 3 http://localhost:9222/json/version >/dev/null 2>&1; then
  echo "✓ Brave con debugging ya está abierto."
else
  echo "Abriendo Brave..."
  "$BRAVE" --remote-debugging-port=9222 --user-data-dir="$PERFIL" >/dev/null 2>&1 &
  for i in $(seq 1 30); do
    curl -s -m 2 http://localhost:9222/json/version >/dev/null 2>&1 && break
    sleep 1
  done
  if ! curl -s -m 2 http://localhost:9222/json/version >/dev/null 2>&1; then
    echo "✗ No se pudo abrir Brave con debugging."
    read -r -p "Enter para cerrar..." _; exit 1
  fi
  echo "✓ Brave listo."
fi

# 2) Radar (busca, filtra, baja DBC, clasifica) — fecha automática
echo ""; echo ">>> 1/2  Radar (buscando convocatorias nuevas)..."
"$PY" radar.py --auto || echo "⚠ radar.py terminó con error (sigo)."

# 3) Especificaciones del DBC
echo ""; echo ">>> 2/2  Extrayendo especificaciones del DBC..."
"$PY" dbc_specs.py || echo "⚠ dbc_specs.py terminó con error (sigo)."

echo ""
echo "✅ Listo. Abrí el dashboard (Radar) para ver las novedades."
echo "   (Podés cerrar la ventana de Brave si querés.)"
read -r -p "Presioná Enter para cerrar esta ventana..." _
