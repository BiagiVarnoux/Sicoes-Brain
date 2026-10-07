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
# OJO: "led" se quitó a propósito — en SICOES casi siempre es alumbrado
# público / luminarias / lámparas, no pantallas. Generaba muchos falsos
# positivos. Las pantallas se pescan con "monitor"/"pantalla"/"televisor".
TERMINOS_PALABRA = [
    "pc", "cpu", "ram", "ssd", "hdd", "ssds", "usb", "ups", "nas",
    "cpus", "gpu", "lcd", "lto", "pdu", "pvc", "nvr",
]

# Si aparece alguno de estos, se descarta el match (cortar falsos positivos).
# Empezamos vacío; se llena cuando veamos ruido real en los objetos.
EXCLUIR = [
    # Falsos positivos reales vistos en corridas (si aparecen, descartar aunque
    # matcheen algún término como "monitor" o "impresora"):
    "signos vitales",       # "monitor de signos vitales" (equipo médico)
    "impresora 3d",         # impresoras 3D (no es su rubro)
    "impresion 3d",
    "alumbrado publico",    # redundante con quitar "led", pero por si acaso
    "luminaria",
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


# Compuerta AMPLIA: términos que indican que un objeto PODRÍA ser de tus rubros
# (computación/electrónica/oficina/etiquetas). Es a propósito laxa — sirve para NO
# mandar a la IA los Bienes obviamente ajenos (medicamentos, alimentos, obras,
# mobiliario, vehículos, etc.), que son la gran mayoría. La IA solo juzga lo que
# pasa esta compuerta (o lo que ya matcheó el diccionario preciso).
_GATE_TERMINOS = [
    "comput", "informat", "electronic", "tecnolog", "periferic", "accesorio",
    "hardware",
    "disco", "memoria", "ram", "ssd", "hdd", "almacenamiento", "nvme",
    "procesador", "placa madre", "tarjeta de", "tarjeta pvc", "usb", "pendrive",
    "monitor", "televisor", "proyector", "teclado", "mouse", "raton",
    "webcam", "parlante", "altavoz", "audifono", "auricular", "microfono",
    "adaptador", "conversor", "docking", "hdmi", "router", "switch",
    "access point", "servidor", "rack", "estabilizador",
    "impres", "escaner", "scanner", "fotocopiad", "plotter", "toner",
    "cartucho", "tinta", "ribbon", "cinta lto", "lto", "backup",
    "etiqueta", "autoadhesiv", "rotulo", "sticker", "codigo de barras",
    "carnet", "ymcko", "zebra", "laptop", "notebook", "portatil", "tablet",
    # electrónica / comunicaciones (recupera lo que la IA sí pescaba)
    "comunicacion", "fibra optica", "fibra", "cable", "telefon", "camara",
    "video", "audio", "sonido", "antena", "radio", "bateria", "cargador",
    "fuente de poder", "energia solar", "panel solar", "sensor", "gps",
]


def posible_tech(objeto: str) -> bool:
    """Compuerta amplia: True si el objeto PODRÍA ser de los rubros (para filtrar
    antes de la IA). Laxa a propósito (prioriza no perder nada)."""
    n = normalizar(objeto)
    return any(t in n for t in _GATE_TERMINOS)


# Categorías de Bienes CLARAMENTE ajenas a los rubros (salud, alimentos, obras,
# vehículos, mobiliario, limpieza, agro...). Si el objeto cae acá, NO se manda a la
# IA (sería gastar API en algo seguro-no). Es una exclusión conservadora: ante la
# duda NO se excluye (que lo juzgue la IA). El diccionario igual corre siempre.
_AJENO_TERMINOS = [
    # salud / médico
    "medicament", "farmac", "insumo medico", "insumos medicos", "material medico",
    "reactivo", "quirurgic", "odontolog", "suero", "vacuna", "jeringa", "gasa",
    "sonda", "cateter", "protesis", "ortesis", "biomedic", "dispositivo medico",
    "material de curacion", "oxigeno medic", "nutricional", "complemento nutri",
    "medico ", "hospitalari", "sanitario para", "leche ", "micronutri",
    # alimentos
    "aliment", "viver", "comestible", "racion", "desayuno", "refrigerio",
    "abarrote", "carne", "pollo", "verdura", "fruta", "pan ", "harina", "arroz",
    "azucar", "aceite comestible",
    # obras / construcción
    "obra ", "obras ", "construccion", "paviment", "asfalt", "hormigon",
    "cemento", "agregado", "ripio", "arena", "ladrillo", "alcantarill",
    "material de construccion", "fierro de construccion", "tuberia", "pvc sanitari",
    "aridos", "enlosetado", "adoquin", "refaccion de", "mantenimiento de infraestru",
    # vehículos / combustible
    "vehiculo", "automovil", "camion", "camioneta", "motocicleta", "llanta",
    "neumatic", "combustible", "gasolina", "diesel", "lubricante", "repuesto automotriz",
    "repuestos para vehic",
    # mobiliario / textil / vestuario
    "mobiliario", "mueble", "silla ", "sillas ", "estante", "textil", "uniforme",
    "ropa ", "calzado", "tela ", "cortina", "colchon", "frazada", "vestuario",
    # limpieza / aseo
    "limpieza", "material de aseo", "detergente", "desinfectante", "higienic",
    # agro
    "semilla", "fertilizante", "agroquimic", "plaguicida", "pecuari", "ganado",
    "agricol", "sistema de riego", "veterinari",
]


def es_claramente_ajeno(objeto: str) -> bool:
    """True si el objeto es de una categoría obviamente ajena a los rubros. Si NO
    matchea el diccionario y NO es claramente ajeno, se manda a la IA para que lo
    juzgue por contexto."""
    n = normalizar(objeto)
    return any(t in n for t in _AJENO_TERMINOS)


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
