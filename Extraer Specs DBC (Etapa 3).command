#!/bin/bash
# Doble clic: extrae las ESPECIFICACIONES TÉCNICAS de los DBC con la API (Groq),
# leyendo el texto del docx. Es REANUDABLE:
#   · Cada proceso se guarda apenas termina.
#   · Cuando las 4 cuentas se quedan sin cupo del día, avisa y se detiene: podés
#     CERRAR la ventana y volver a correr este comando otro día — continúa solo.
#   · Al reanudar, re-hace el ÚLTIMO proceso (por si quedó incompleto).
set -u
set -o pipefail
trap 'exit 130' INT TERM
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT" || exit 1
export PYTHONDONTWRITEBYTECODE=1

PY=""
for c in "$ROOT/scraper/venv/bin/python" "$ROOT/scraper/historico_local/.venv/bin/python"; do
  [ -x "$c" ] && { PY="$c"; break; }
done
[ -z "$PY" ] && { echo "No se encontró el entorno virtual"; read -r -p "Enter para cerrar..." _; exit 1; }

# Última corrida de la etapa 2 (carpeta con las fichas) — se detecta sola.
RUN="$(ls -dt "$ROOT"/procesamiento/historico/data/adquisiciones_etapa2_* 2>/dev/null | head -1)"
[ -z "$RUN" ] && { echo "No hay salida de la etapa 2 (adquisiciones_etapa2_*)"; read -r -p "Enter para cerrar..." _; exit 1; }

echo "════════════════════════════════════════════"
echo "   ETAPA 3 — Especificaciones técnicas del DBC"
echo "   Corrida: $(basename "$RUN")"
echo "════════════════════════════════════════════"
"$PY" -B -m procesamiento.historico.extraer_specs --run "$RUN" --estado 2>/dev/null
echo "--------------------------------------------"
echo "Empezando/continuando. No cierres hasta que avise (o hasta que termine)."
echo ""

if command -v caffeinate >/dev/null 2>&1; then
  caffeinate -dimsu "$PY" -B -m procesamiento.historico.extraer_specs --run "$RUN"
else
  "$PY" -B -m procesamiento.historico.extraer_specs --run "$RUN"
fi

echo ""
echo "════════════════════════════════════════════"
read -r -p "Listo por ahora. Presioná Enter para cerrar esta ventana..." _
