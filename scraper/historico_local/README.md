# Scraper histórico documental local

Desde la raíz de SICOES-BRAIN:

```sh
./"Correr Sicoes Local.command" --check
./"Correr Sicoes Local.command"
```

El primer comando verifica dependencias sin navegador ni conexiones. El segundo
inicia captura real y debe ejecutarse solo por decisión del operador. Pide entidad
y gestiones, admite rangos y deduplica años. Alcance: Bienes, estado 2C,
CM/ANPE/ANPP/LP. Procesa cada página antes de avanzar, verifica el total avanzado,
conserva reanudación y evidencia parcial cuando no puede confirmar cobertura.

Usa `SICOES_LOCAL_PYTHON` si se necesita otro intérprete; de forma predeterminada
busca el entorno local del paquete y después `scraper/venv/bin/python`.
No instala dependencias. Consultar requirements.txt; pypdf es opcional para el
convertidor auxiliar preservado, no para la captura operativa con MarkItDown.

CLI: `python -B -m scraper.historico_local --entidad 0660-10 --anio 2024`.
Brave: puerto 9226, perfil exclusivo `data/brave-historico-http/` dentro del
paquete. No ejecutar simultáneamente los ejecutores del experimental en 9226.
La sesión antigua no se migra: resolver manualmente captcha/comunicados en el
nuevo perfil. No se automatiza su evasión.

Salidas futuras en `data/historico_http_paginas_<entidad>_<anio>/`; logs en
`data/historico_http_paginas_logs/`, auxiliares y perfil también en data/.
Los corpus 0660-10 de 2022, 2023 y 2024 ya están en la ubicación definitiva,
trasladados por el usuario y verificados por SHA256. Los manifiestos conservan versiones, hashes,
intentos, originales y derivados. PDF sin texto queda FALTA_OCR, sin ejecutar OCR.
No hay escritores Supabase ni carga de .env en el camino operativo.

Reutiliza por AST funciones de los scrapers existentes, sin importar sus clientes.
La descarga de adjuntos conserva el hook temporal submit/requestSubmit y la
petición por context.request que evita abrir ventanas. El fallback nativo puede
traer Brave al frente. No se modifican los scrapers base.

storage.py, parsing.py y brave_bootstrap.py conservan sus funciones auxiliares
por decisión de integración conservadora. schema.sql permite utilizar Store si
se lo invoca explícitamente; la captura anual no lo utiliza. No se incorporan
engine, browser, session ni el CLI de cinco CUCE.

Pruebas sintéticas: `python -B -m unittest discover -s scraper/historico_local/tests -v`.
El informe de integración registra ejecución sin red y conservación de main.
