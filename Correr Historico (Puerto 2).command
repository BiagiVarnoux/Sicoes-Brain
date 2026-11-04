#!/bin/bash
# ───────────────────────────────────────────────────────────────────────────
# SEGUNDA corrida en paralelo (puerto 9223, perfil de Brave aparte).
# Doble clic para barrer OTRA entidad al mismo tiempo que la corrida principal.
# Reutiliza toda la lógica de "Correr Historico.command"; solo cambia el puerto
# y el perfil para no chocar con la otra ventana de Brave.
# ───────────────────────────────────────────────────────────────────────────
export PUERTO=9223
export PERFIL=/tmp/brave-sicoes-2
exec "/Users/fabriziocuellar/Sicoes-Brain/Correr Historico.command"
