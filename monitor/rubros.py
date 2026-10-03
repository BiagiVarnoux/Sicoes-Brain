"""
Filtro A — Diccionario de rubros
================================
Clasifica una convocatoria por su "Objeto de Contratación" buscando términos
conocidos de los rubros del usuario: productos/accesorios de computación y
etiquetas autoadhesivas.

Este diccionario se va REFINANDO con los objetos reales que devuelve el radar
(ver monitor/salidas/objetos_*.csv). Agregá/quitá términos acá y volvé a correr.

Diseño:
- Términos multi-palabra se buscan como substring (ya normalizado).
- Términos cortos y ambiguos (ram, pc, cpu, ssd, hdd, ups, red) se buscan con
  límite de palabra (\\b) para no matchear "programa", "red" en "credencial", etc.
- EXCLUIR: si el objeto contiene alguno de estos, se descarta aunque matchee
  (sirve para cortar falsos positivos típicos; empezar vacío e ir agregando).
"""
import re
import unicodedata

# ─── Términos de los rubros ───────────────────────────────────────────────────
# Multi-palabra o inequívocos (substring sobre texto normalizado sin acentos).
TERMINOS_SUBSTRING = [
    # Computación — equipos
    "computador", "computadora", "computadoras", "laptop", "notebook",
    "estacion de trabajo", "workstation", "all in one", "mini pc",
    "equipo de computacion", "equipos de computacion", "equipo informatico",
    "equipos informaticos", "material informatico", "hardware",
    # Componentes / almacenamiento
    "memoria ram", "memorias ram", "modulo de memoria", "memoria ddr",
    "ddr4", "ddr5",
    "disco solido", "discos solido", "disco de estado solido",
    "discos de estado solido", "estado solido", "unidad de estado solido",
    "disco duro", "discos duro", "disco rigido", "nvme", "almacenamiento",
    "storage", "servidor", "servidores", "pdu", "rack",
    "procesador", "placa madre", "tarjeta madre", "motherboard",
    "fuente de poder", "fuente de alimentacion", "tarjeta de video",
    "tarjeta grafica", "tarjeta de red", "memoria usb", "pen drive",
    "pendrive", "flash memory", "tarjeta de memoria", "micro sd", "microsd",
    # Periféricos / accesorios
    "periferico", "perifericos", "accesorio de computacion",
    "accesorios de computacion", "teclado", "mouse", "raton",
    "monitor", "pantalla", "webcam", "camara web", "audifono", "auricular",
    "parlante", "microfono", "hub usb", "docking", "adaptador",
    "cable hdmi", "cable vga", "cable usb",
    # Impresión / consumibles
    "impresora", "impresoras", "multifuncional", "multifuncion", "fotocopiadora",
    "escaner", "escaners", "scanner", "scanners", "plotter",
    "toner", "cartucho", "tinta", "cinta de impresion", "ribbon",
    "consumible de impresion", "consumibles de impresion",
    "carnet", "carnets", "tarjeta pvc", "tarjetas pvc",
    # Almacenamiento en cinta / backup
    "cinta lto", "cintas lto", "lto9", "cinta de backup", "cintas de backup",
    "backup", "backups",
    # Redes / energía
    "router", "switch", "access point", "cable utp", "cable de red",
    "patch panel", "ups", "estabilizador", "estabilizadores",
    # Informática (genérico) / displays
    "informatico", "informatica", "parque informatico",
    "televisor", "televisores",
    # Etiquetas / papel autoadhesivo
    "etiqueta autoadhesiva", "etiquetas autoadhesivas", "etiqueta adhesiva",
    "etiquetas adhesivas", "etiqueta", "etiquetas", "etiqueta continua",
    "autoadhesivo", "autoadhesiva", "papel autoadhesivo",
    "sticker", "stickers", "rotulo", "rotulos",
    "impresora de etiquetas", "codigo de barras",
]

# Cortos/ambiguos — se exigen con límite de palabra.
TERMINOS_PALABRA = [
    "pc", "cpu", "ram", "ssd", "hdd", "ssds", "usb", "ups", "nas",
    "cpus", "gpu", "led", "lcd", "lto", "pdu", "pvc", "nvr",
]

# Si aparece alguno de estos, se descarta el match (cortar falsos positivos).
# Empezamos vacío; se llena cuando veamos ruido real en los objetos.
EXCLUIR = [
    # p.ej. "servicio de impresion" si solo buscamos el bien físico:
    # "servicio de impresion",
]


def normalizar(texto: str) -> str:
    """minúsculas, sin acentos, espacios colapsados."""
    if not texto:
        return ""
    t = unicodedata.normalize("NFKD", texto)
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = t.lower()
    t = re.sub(r"\s+", " ", t).strip()
    return t


# Precompilar regex de palabra
_RE_PALABRA = {t: re.compile(rf"\b{re.escape(t)}\b") for t in TERMINOS_PALABRA}


def match_rubros(objeto: str) -> list[str]:
    """Devuelve la lista de términos que matchearon (vacía si ninguno)."""
    n = normalizar(objeto)
    if not n:
        return []
    for ex in EXCLUIR:
        if normalizar(ex) in n:
            return []
    hits = []
    for t in TERMINOS_SUBSTRING:
        if t in n:
            hits.append(t)
    for t, rx in _RE_PALABRA.items():
        if rx.search(n):
            hits.append(t)
    # dedup conservando orden
    vistos = set()
    out = []
    for h in hits:
        if h not in vistos:
            vistos.add(h)
            out.append(h)
    return out
