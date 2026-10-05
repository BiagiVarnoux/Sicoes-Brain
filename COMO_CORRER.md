# Cómo correr el Radar — pasos

> Todos los comandos de Python usan el venv del scraper: `../scraper/venv/bin/python`
> (o desde la raíz: `scraper/venv/bin/python`). Configuración en `monitor/.env`.

## 🟢 Uso normal (revisar oportunidades nuevas)

### 1. Abrir Brave con debugging
Cerrá Brave del todo y abrilo así:
```bash
/Applications/Brave\ Browser.app/Contents/MacOS/Brave\ Browser --remote-debugging-port=9222 --user-data-dir="/tmp/brave-sicoes"
```
Entrá a `https://www.sicoes.gob.bo/portal/index.php` y cerrá el popup de comunicados.

### 2. Correr el radar (busca, filtra, baja y clasifica)
```bash
cd /Users/fabriziocuellar/Sicoes-Brain/monitor
../scraper/venv/bin/python radar.py --desde DD/MM/2026
```
- Sin `--desde`, usa los últimos 7 días.
- Hace todo: busca Bienes por fecha → filtra (modalidad/estado/abiertas) → doble
  filtro (diccionario + IA con tu catálogo del ERP) → baja el DBC/Oferta, lo
  convierte a PDF y lo sube → guarda en la base.

### 3. Extraer las especificaciones del DBC
```bash
../scraper/venv/bin/python dbc_specs.py
```
Lee los DBC nuevos y extrae las specs técnicas (panel "📋 Qué pide la entidad").

### 4. Ver en el dashboard
Abrí el radar desplegado en Vercel. Ahí ves: filtros, DBC descargable, tu historial
de precios y lo que pide la entidad. Marcás **Visto** / **Descartar** (con motivos).

---

## 🔄 Cada tanto (mantener el historial del ERP al día)

### Refrescar el historial del ERP (cuando cargás licitaciones nuevas en el ERP)
```bash
cd /Users/fabriziocuellar/Sicoes-Brain/monitor
../scraper/venv/bin/python erp_sync.py
```
Actualiza el badge "Ya trabajada", el catálogo que usa la IA y tu historial de precios.

### Parsear los Formularios C-1 (requerimiento entidad vs tu oferta)
```bash
../scraper/venv/bin/python c1_parse.py
```
Una vez por documento (cacheado). Para reprocesar todo: `c1_parse.py --reparse`.

---

## 📌 Orden recomendado de una sesión típica
1. Abrir Brave (paso 1).
2. `radar.py --desde <última fecha que revisaste>`  (paso 2)
3. `dbc_specs.py`  (paso 3)
4. Revisar en el dashboard y descartar lo que no sirve.
5. (Opcional) `erp_sync.py` si cargaste cosas nuevas en el ERP.

## ⚙️ Notas
- **Groq (IA)** tiene límite de 8.000 tokens/min (plan gratuito); por eso
  `dbc_specs.py` y `c1_parse.py` van con pausas. Si subís de plan, vuelan.
- Los descartes por **"producto"** entrenan la IA en la próxima corrida.
- Si Brave se cierra a mitad, los scripts reconectan; volvé a correr y sigue donde quedó.
