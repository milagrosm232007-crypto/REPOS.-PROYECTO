"""
backend.py
==========
Logica de monitoreo y ciberseguridad de MemGuard.

Este modulo NO dibuja nada en pantalla: solo obtiene datos del sistema
(psutil) y evalua reglas de seguridad. La interfaz (interface.py) lo
importa y muestra los resultados en las 8 pantallas del wireframe.

Requiere:  pip install psutil pyttsx3
"""

import os
import platform
import json
import time
import re
import threading
import hashlib
import subprocess
import shutil
from datetime import datetime

import psutil

# --------------------------------------------------------------------------
# Constantes de ciberseguridad
# --------------------------------------------------------------------------
PUERTOS_CONOCIDOS = {
    21: "FTP", 22: "SSH", 23: "Telnet", 80: "HTTP", 135: "RPC",
    139: "NetBIOS", 443: "HTTPS", 445: "SMB", 3389: "RDP", 5900: "VNC"
}
PUERTOS_RIESGO = {21, 23, 135, 139, 445, 3389, 5900}
RUTAS_SOSPECHOSAS = [
    "\\temp\\", "\\appdata\\roaming\\",
    "\\appdata\\local\\temp\\", "\\users\\public\\"
]
MALWARE_CONOCIDO = {
    "mimikatz.exe", "nc.exe", "ncat.exe",
    "netcat.exe", "psexec.exe", "wce.exe", "pwdump.exe"
}

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
CREDENCIALES_PATH = os.path.join(os.path.dirname(__file__), "credenciales.json")
DEFAULT_CONFIG = {
    "intervalo_escaneo": 10,
    "lenguaje": "Python 3.x",
    "entorno_virtual": "VirtualBox",
    "version": "v1.0 beta",
    "libreria_voz": "pyttsx3",
    "voz_id": "",
    "texto_grande": True,
    "alto_contraste": True,
    "modo_oscuro": False,
    "alertas_sonoras": False,
    "modo_desarrollador": False,
}
CREDENCIALES_POR_DEFECTO = {
    "usuario": "admin@memguard.py",
    "hash": hashlib.sha256("memguard123".encode("utf-8")).hexdigest(),
}


# --------------------------------------------------------------------------
# Autenticacion (Pantalla 1: Login)
# --------------------------------------------------------------------------
def _hash_contrasena(texto):
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def cargar_credenciales():
    if os.path.exists(CREDENCIALES_PATH):
        try:
            with open(CREDENCIALES_PATH, "r", encoding="utf-8") as f:
                datos = json.load(f)
            if "usuario" in datos and "hash" in datos:
                return datos
        except (json.JSONDecodeError, OSError):
            pass
    guardar_credenciales(CREDENCIALES_POR_DEFECTO)
    return CREDENCIALES_POR_DEFECTO.copy()


def guardar_credenciales(credenciales):
    with open(CREDENCIALES_PATH, "w", encoding="utf-8") as f:
        json.dump(credenciales, f, indent=4, ensure_ascii=False)


def verificar_credenciales(usuario, contrasena):
    cred = cargar_credenciales()
    return (
        usuario.strip().lower() == cred["usuario"].strip().lower()
        and _hash_contrasena(contrasena) == cred["hash"]
    )


def cambiar_contrasena(contrasena_actual, contrasena_nueva, usuario_nuevo=None):
    """Cambia la contrasena solo si la actual es correcta.
    Retorna (exito: bool, mensaje: str)."""
    cred = cargar_credenciales()
    if _hash_contrasena(contrasena_actual) != cred["hash"]:
        return False, "La contrasena actual no es correcta."
    if not contrasena_nueva or len(contrasena_nueva) < 6:
        return False, "La nueva contrasena debe tener al menos 6 caracteres."
    cred["hash"] = _hash_contrasena(contrasena_nueva)
    if usuario_nuevo:
        cred["usuario"] = usuario_nuevo.strip()
    guardar_credenciales(cred)
    return True, "Contrasena actualizada correctamente."


# --------------------------------------------------------------------------
# Monitoreo basico (Pantalla 2: Panel principal / Pantalla 3: Memoria RAM)
# --------------------------------------------------------------------------
def obtener_cpu():
    """Porcentaje de uso de CPU (0-100)."""
    return psutil.cpu_percent(interval=0.3)


def obtener_ram():
    memoria = psutil.virtual_memory()
    return {
        "uso_percent": memoria.percent,
        "total_gb": round(memoria.total / (1024 ** 3), 2),
        "usado_gb": round((memoria.total - memoria.available) / (1024 ** 3), 2),
        "disponible_gb": round(memoria.available / (1024 ** 3), 2),
    }


def obtener_sistema():
    return {
        "sistema": platform.system(),
        "version": platform.release(),
        "equipo": platform.node(),
        "arquitectura": platform.machine(),
    }


def _unidad_por_defecto():
    """En Windows la unidad principal es C:\\, en Linux/Mac es /."""
    return "C:\\" if platform.system() == "Windows" else "/"


def obtener_disco(unidad=None):
    unidad = unidad or _unidad_por_defecto()
    disco = psutil.disk_usage(unidad)
    return {
        "unidad": unidad,
        "total_gb": round(disco.total / (1024 ** 3), 2),
        "usado_gb": round(disco.used / (1024 ** 3), 2),
        "libre_gb": round(disco.free / (1024 ** 3), 2),
        "porcentaje": disco.percent,
    }


def _es_removible(particion):
    """En Windows psutil marca 'removable' en las opciones. En Linux no
    existe esa bandera, asi que se usa el punto de montaje como pista
    (USB suele montarse en /media/, /run/media/ o /mnt/)."""
    if "removable" in particion.opts:
        return True
    if platform.system() != "Windows":
        # /media/ y /run/media/ son las rutas estandar donde Linux monta
        # automaticamente los USB. Se deja fuera /mnt/ a proposito, porque
        # tambien se usa para montajes manuales que no son USB.
        prefijos = ("/media/", "/run/media/")
        return particion.mountpoint.startswith(prefijos)
    return False


def detectar_usb():
    """Retorna el estado del primer dispositivo extraible encontrado."""
    for particion in psutil.disk_partitions():
        if _es_removible(particion):
            return {"usb_detectado": True, "unidad": particion.mountpoint}
    return {"usb_detectado": False, "unidad": None}


def listar_usb():
    """Retorna TODOS los dispositivos extraibles (Pantalla 4)."""
    dispositivos = []
    for particion in psutil.disk_partitions():
        if not _es_removible(particion):
            continue
        try:
            uso = psutil.disk_usage(particion.mountpoint)
            total_gb = round(uso.total / (1024 ** 3), 2)
        except (PermissionError, FileNotFoundError, OSError):
            total_gb = 0
        alerta_autorun = os.path.exists(
            os.path.join(particion.mountpoint, "autorun.inf")
        ) if os.path.exists(particion.mountpoint) else False
        dispositivos.append({
            "nombre": f"USB {total_gb} GB" if total_gb else "USB",
            "unidad": particion.mountpoint,
            "device": particion.device,
            "sistema_archivos": particion.fstype or "?",
            "total_gb": total_gb,
            "sospechoso": alerta_autorun,
        })
    return dispositivos


def obtener_info_usb(unidad):
    uso = psutil.disk_usage(unidad)
    return {
        "unidad": unidad,
        "total_gb": round(uso.total / (1024 ** 3), 2),
        "usado_gb": round(uso.used / (1024 ** 3), 2),
        "libre_gb": round(uso.free / (1024 ** 3), 2),
        "porcentaje": uso.percent,
    }


def obtener_procesos(top=10):
    """Top procesos por uso de CPU (Pantalla 3)."""
    procesos = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
        try:
            mem_mb = round(proc.info['memory_info'].rss / (1024 ** 2), 1) if proc.info['memory_info'] else 0
            procesos.append({
                "pid": proc.info['pid'],
                "nombre": proc.info['name'] or "?",
                "cpu": proc.info['cpu_percent'] or 0.0,
                "mem_mb": mem_mb,
                "estado": clasificar_proceso(proc.info['cpu_percent'] or 0.0),
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    procesos.sort(key=lambda p: p["mem_mb"], reverse=True)
    return procesos[:top]


def clasificar_proceso(cpu):
    if cpu >= 50:
        return "Alto"
    if cpu >= 10:
        return "Normal"
    return "OK"


# --------------------------------------------------------------------------
# Ciberseguridad (Pantalla 5: Ciberseguridad / Pantalla 6: Alertas)
# --------------------------------------------------------------------------
def detectar_puertos():
    alertas = []
    try:
        for c in psutil.net_connections(kind="inet"):
            if c.status == "LISTEN" and c.laddr.port in PUERTOS_RIESGO:
                p = c.laddr.port
                alertas.append(("ALTO", f"Puerto {p} ({PUERTOS_CONOCIDOS[p]}) expuesto en LISTEN", "Ciberseg."))
    except psutil.AccessDenied:
        alertas.append(("INFO", "Ejecutar como Administrador para ver puertos", "Ciberseg."))
    return alertas


def detectar_conexiones():
    alertas = []
    LAN = ("127.", "10.", "192.168.", "::1")
    try:
        for c in psutil.net_connections(kind="inet"):
            if c.status != "ESTABLISHED" or not c.raddr:
                continue
            ip, puerto = c.raddr.ip, c.raddr.port
            if any(ip.startswith(p) for p in LAN):
                continue
            if puerto not in PUERTOS_CONOCIDOS:
                alertas.append(("MEDIO", f"Conexion externa sospechosa: {ip}:{puerto} - puerto no estandar", "Red"))
    except psutil.AccessDenied:
        alertas.append(("INFO", "Ejecutar como Administrador para ver conexiones", "Red"))
    return alertas


def detectar_procesos_sospechosos():
    alertas = []
    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        try:
            nombre = (proc.info['name'] or "").lower()
            ruta = (proc.info['exe'] or "").lower()
            if nombre in MALWARE_CONOCIDO:
                alertas.append(("ALTO", f"PID {proc.info['pid']} - herramienta ofensiva detectada: {proc.info['name']}", "Analisis"))
            elif any(rs in ruta for rs in RUTAS_SOSPECHOSAS):
                alertas.append(("MEDIO", f"PID {proc.info['pid']} ({proc.info['name']}) ejecutando desde ruta sospechosa", "Analisis"))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return alertas


def auditar_seguridad_usb(punto_montaje):
    """Solo agrega una alerta si encuentra algo realmente sospechoso.
    Un USB limpio no genera ningun mensaje (ni siquiera informativo),
    para que la lista de alertas quede vacia de verdad cuando todo
    esta bien."""
    alertas = []
    if not punto_montaje:
        return alertas
    try:
        ruta_autorun = os.path.join(punto_montaje, "autorun.inf")
        if os.path.exists(ruta_autorun):
            alertas.append(("ALTO", f"Dispositivo USB en {punto_montaje} - autorun.inf sospechoso", "USB"))
    except Exception as e:
        alertas.append(("MEDIO", f"Error al monitorear USB: {e}", "USB"))
    return alertas


def obtener_alertas():
    """
    Unifica todas las alertas de seguridad en una sola lista de diccionarios,
    lista para pintar en las pantallas 'Ciberseguridad' y 'Alertas'.
    """
    usb = detectar_usb()
    unidad_usb = usb["unidad"] if usb["usb_detectado"] else None

    crudas = (
        detectar_puertos()
        + detectar_conexiones()
        + detectar_procesos_sospechosos()
        + auditar_seguridad_usb(unidad_usb)
    )
    orden = {"ALTO": 0, "MEDIO": 1, "INFO": 2}
    crudas.sort(key=lambda a: orden[a[0]])

    ahora = datetime.now().strftime("%H:%M")
    alertas = [
        {"nivel": nivel, "mensaje": mensaje, "categoria": categoria, "hora": ahora}
        for nivel, mensaje, categoria in crudas
    ]
    return alertas


def resumen_ciberseguridad(alertas=None):
    alertas = alertas if alertas is not None else obtener_alertas()
    amenazas = sum(1 for a in alertas if a["nivel"] == "ALTO")
    return {
        "amenazas": amenazas,
        "estado": "ALERTA" if amenazas > 0 else "SEGURO",
        "total": len(alertas),
    }


# --------------------------------------------------------------------------
# Estado general (usado por Pantalla 2: Panel principal)
# --------------------------------------------------------------------------
def obtener_estado_sistema():
    disco = obtener_disco()
    usb = detectar_usb()
    ram = obtener_ram()
    cpu = obtener_cpu()
    sistema = obtener_sistema()
    procesos = obtener_procesos()
    alertas = obtener_alertas()

    resultado = {
        "cpu": cpu,
        "ram": ram,
        "disco": disco,
        "usb": usb,
        "procesos": {"cantidad": len(procesos), "lista": procesos},
        "sistema": sistema,
        "alertas": alertas,
    }
    if usb["usb_detectado"]:
        resultado["info_usb"] = obtener_info_usb(usb["unidad"])
    return resultado


# --------------------------------------------------------------------------
# Modo desarrollador (Pantalla 8: Configuracion)
# --------------------------------------------------------------------------
def ejecutar_diagnostico_rendimiento():
    """Corre un ciclo completo de obtener_estado_sistema() y mide cuanto
    tarda de verdad, para que el modo desarrollador pueda ver el costo
    real de un escaneo (no es una simulacion, es el mismo trabajo que
    hacen las pantallas de rendimiento)."""
    inicio = time.perf_counter()
    estado = obtener_estado_sistema()
    duracion_ms = round((time.perf_counter() - inicio) * 1000, 1)
    return {
        "duracion_ms": duracion_ms,
        "cpu": estado["cpu"],
        "ram_percent": estado["ram"]["uso_percent"],
        "procesos_analizados": estado["procesos"]["cantidad"],
        "amenazas": len(estado["alertas"]),
        "hora": datetime.now().strftime("%H:%M:%S"),
    }


def _tarea_estres(hasta):
    """Carga de CPU real (busy loop) hasta el instante 'hasta' (time.time())."""
    while time.time() < hasta:
        pass


def ejecutar_prueba_estres(segundos=5):
    """Genera carga real de CPU en varios nucleos durante 'segundos', para
    que se pueda observar el efecto en las pantallas de Memoria RAM /
    Control de amenazas mientras corre. Es BLOQUEANTE (espera a que
    termine), asi que siempre se debe llamar desde un hilo en segundo
    plano y nunca desde el hilo de la interfaz grafica.

    Tiene un limite de seguridad de 30 segundos para que un boton de
    prueba no pueda dejar la maquina colgada por error."""
    segundos = max(1, min(int(segundos), 30))
    nucleos = max(1, (os.cpu_count() or 1) - 1)  # deja un nucleo libre para la UI
    fin = time.time() + segundos
    hilos = [threading.Thread(target=_tarea_estres, args=(fin,), daemon=True)
             for _ in range(nucleos)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    return {"segundos": segundos, "nucleos_usados": nucleos}


def medir_latencia(host="8.8.8.8", cantidad=4):
    """Mide la latencia de red real haciendo ping a 'host' (por defecto,
    un DNS publico que casi siempre responde, para no depender de que el
    usuario conozca su gateway). Usa el comando 'ping' del sistema
    operativo (multiplataforma) en vez de abrir sockets a mano, asi
    respeta firewalls/ICMP igual que lo haria el usuario desde una
    terminal.

    Retorna un dict con el promedio en ms, perdida de paquetes y la
    calidad estimada, o exito=False con un mensaje si no se pudo medir
    (por ejemplo, sin conexion a internet)."""
    sistema = platform.system()
    try:
        if sistema == "Windows":
            comando = ["ping", "-n", str(cantidad), "-w", "2000", host]
        else:
            comando = ["ping", "-c", str(cantidad), "-W", "2", host]

        inicio = time.perf_counter()
        resultado = subprocess.run(
            comando, capture_output=True, text=True, timeout=cantidad * 3 + 5
        )
        duracion_total_ms = round((time.perf_counter() - inicio) * 1000, 1)
        salida = resultado.stdout or ""

        promedio_ms = None
        perdida_percent = None

        # Windows: "Perdidos = 0 (0% perdidos)" / "Media = 23ms"
        m_perdida = re.search(r"(\d+)%\s*(?:perdidos|loss)", salida, re.IGNORECASE)
        if m_perdida:
            perdida_percent = int(m_perdida.group(1))
        m_media = re.search(r"(?:Media|Average|Avg)\s*=?\s*([\d.]+)\s*ms", salida, re.IGNORECASE)
        if m_media:
            promedio_ms = float(m_media.group(1))
        else:
            # Linux/Mac: "rtt min/avg/max/mdev = 12.1/23.4/45.0/10.2 ms"
            m_rtt = re.search(r"=\s*[\d.]+/([\d.]+)/[\d.]+/[\d.]+\s*ms", salida)
            if m_rtt:
                promedio_ms = float(m_rtt.group(1))

        if resultado.returncode != 0 or promedio_ms is None:
            return {
                "exito": False,
                "host": host,
                "mensaje": "No se obtuvo respuesta del host (sin conexion a internet o bloqueado por firewall).",
                "hora": datetime.now().strftime("%H:%M:%S"),
            }

        if promedio_ms < 60:
            calidad = "Excelente"
        elif promedio_ms < 150:
            calidad = "Buena"
        elif promedio_ms < 300:
            calidad = "Regular"
        else:
            calidad = "Mala"

        return {
            "exito": True,
            "host": host,
            "promedio_ms": round(promedio_ms, 1),
            "perdida_percent": perdida_percent if perdida_percent is not None else 0,
            "calidad": calidad,
            "duracion_total_ms": duracion_total_ms,
            "hora": datetime.now().strftime("%H:%M:%S"),
        }
    except FileNotFoundError:
        return {
            "exito": False, "host": host,
            "mensaje": "No se encontro el comando 'ping' en este sistema.",
            "hora": datetime.now().strftime("%H:%M:%S"),
        }
    except subprocess.TimeoutExpired:
        return {
            "exito": False, "host": host,
            "mensaje": "La medicion tardo demasiado y fue cancelada.",
            "hora": datetime.now().strftime("%H:%M:%S"),
        }
    except Exception as e:
        return {
            "exito": False, "host": host,
            "mensaje": f"Error inesperado al medir la latencia: {e}",
            "hora": datetime.now().strftime("%H:%M:%S"),
        }


# --------------------------------------------------------------------------
# Voz / accesibilidad
# --------------------------------------------------------------------------
_motor_voz = None
_motor_lock = threading.Lock()


def _puntuar_voz(v):
    """Le da mas puntaje a las voces en espanol de mejor calidad. Las voces
    'mbrola' (ej. mb-es1/mb-es2) suenan bastante mas naturales que el
    espeak/espeak-ng comun, asi que se prefieren si estan instaladas."""
    nombre = (v.name or "").lower()
    id_voz = (v.id or "").lower()
    idiomas = " ".join(str(i) for i in (getattr(v, "languages", []) or [])).lower()
    es_espanol = (
        "spanish" in nombre or "espa" in nombre or "es_" in idiomas
        or "es-" in idiomas or nombre.startswith("es") or "es" in id_voz.split("/")[-1][:3]
    )
    if not es_espanol:
        return -1
    puntaje = 1
    if "mb-es" in id_voz or "mbrola" in nombre or "mbrola" in id_voz:
        puntaje = 3  # mbrola: la mejor calidad disponible localmente
    elif "espeak-ng" in id_voz or "ng" in id_voz:
        puntaje = 2  # espeak-ng suena algo mejor que espeak clasico
    return puntaje


def _seleccionar_mejor_voz(motor):
    """Elige automaticamente la mejor voz en espanol disponible (prioriza
    mbrola > espeak-ng > espeak). Se usa cuando no hay una voz elegida a
    mano por el usuario, o cuando este vuelve a 'Automatica'."""
    try:
        voces = motor.getProperty("voices") or []
        candidatas = [(v, _puntuar_voz(v)) for v in voces]
        candidatas = [c for c in candidatas if c[1] > 0]
        if candidatas:
            candidatas.sort(key=lambda c: c[1], reverse=True)
            motor.setProperty("voice", candidatas[0][0].id)
            return True
    except Exception:
        pass
    return False


def _configurar_motor(motor):
    """Ajusta velocidad/volumen/tono y elige la voz a usar: si el usuario
    ya eligio una a mano en Accesibilidad (config 'voz_id'), se respeta
    esa; si no, se elige automaticamente la mejor voz en espanol
    disponible (mbrola > espeak-ng > espeak). Esto evita el sonido
    'atropellado' que da crear un motor nuevo cada vez y deja el
    resultado mas parecido entre Windows (SAPI5) y Linux (espeak/
    espeak-ng/mbrola)."""
    voz_guardada = ""
    try:
        voz_guardada = (cargar_configuracion().get("voz_id") or "").strip()
    except Exception:
        pass
    aplicada = False
    if voz_guardada:
        try:
            motor.setProperty("voice", voz_guardada)
            aplicada = True
        except Exception:
            aplicada = False
    if not aplicada:
        _seleccionar_mejor_voz(motor)
    # 140-155 wpm con un tono un poco mas bajo que el default se entiende
    # notablemente mejor que la voz "de fabrica" (~200 wpm, pitch 50).
    motor.setProperty("rate", 145)
    motor.setProperty("volume", 1.0)
    try:
        # "pitch" solo esta disponible con el driver espeak/espeak-ng
        # (no existe en SAPI5 de Windows), por eso va en su propio
        # try/except: si falla, no debe romper el resto de la configuracion.
        motor.setProperty("pitch", 45)
    except Exception:
        pass


def _obtener_motor():
    global _motor_voz
    if _motor_voz is None:
        import pyttsx3
        _motor_voz = pyttsx3.init()
        _configurar_motor(_motor_voz)
    return _motor_voz


def listar_voces():
    """Devuelve todas las voces de texto a voz instaladas en el sistema
    (id + nombre), para que el usuario pueda elegir una a mano en
    Accesibilidad en vez de dejar que la app la elija sola."""
    try:
        motor = _obtener_motor()
        voces = motor.getProperty("voices") or []
        return [{"id": v.id, "nombre": v.name or v.id} for v in voces]
    except Exception:
        return []


def establecer_voz(voz_id):
    """Cambia la voz del motor ya activo, sin reiniciarlo (para que el
    cambio se sienta inmediato al elegirla en Accesibilidad)."""
    try:
        with _motor_lock:
            motor = _obtener_motor()
            motor.setProperty("voice", voz_id)
        return True
    except Exception:
        return False


def reconfigurar_voz_automatica():
    """Vuelve a dejar que la app elija la mejor voz disponible sola
    (opcion 'Automatica' del selector)."""
    try:
        with _motor_lock:
            motor = _obtener_motor()
            return _seleccionar_mejor_voz(motor)
    except Exception:
        return False


def hablar(texto, velocidad=None):
    """Reproduce una alerta por voz. Usa un unico motor persistente
    protegido por un lock, asi dos alertas nunca hablan al mismo tiempo
    (eso es lo que suena 'raro' o distorsionado). No lanza excepcion si
    la libreria/motor de voz no esta disponible; la interfaz decide como
    avisar al usuario en ese caso."""
    try:
        with _motor_lock:
            motor = _obtener_motor()
            if velocidad:
                motor.setProperty("rate", velocidad)
            motor.say(texto)
            motor.runAndWait()
        return True
    except Exception:
        return False


# --------------------------------------------------------------------------
# Configuracion persistente (Pantalla 8)
# --------------------------------------------------------------------------
def cargar_configuracion():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                datos = json.load(f)
            config = DEFAULT_CONFIG.copy()
            config.update(datos)
            return config
        except (json.JSONDecodeError, OSError):
            pass
    return DEFAULT_CONFIG.copy()


def guardar_configuracion(config):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)


# Firmas binarias (los primeros bytes reales de un archivo) usadas para
# detectar ejecutables disfrazados de otra cosa: un archivo puede
# llamarse "foto.jpg" pero si arranca con estos bytes, es en realidad
# un ejecutable con la extension cambiada a mano.
_FIRMAS_EJECUTABLES = {
    b"MZ": "ejecutable de Windows (.exe/.dll)",
    b"\x7fELF": "ejecutable de Linux (ELF)",
    b"\xca\xfe\xba\xbe": "ejecutable de Mac (Mach-O)",
}
_EXTENSIONES_NO_EJECUTABLES = {
    "jpg", "jpeg", "png", "gif", "bmp", "webp", "ico",
    "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
    "txt", "mp3", "mp4", "avi", "mkv", "wav",
}
_MAX_ARCHIVOS_ESCANEADOS = 4000  # limite de seguridad para USB muy grandes


def _leer_firma(ruta):
    try:
        with open(ruta, "rb") as f:
            return f.read(8)
    except (PermissionError, OSError):
        return b""


def _analizar_autorun(ruta_autorun):
    """Lee el contenido real de autorun.inf (no solo confirma que existe)
    y busca la linea 'open=' o 'shellexecute=', que es la que de verdad
    dispara un programa automaticamente al conectar el USB."""
    try:
        with open(ruta_autorun, "r", encoding="utf-8", errors="ignore") as f:
            contenido = f.read()
        for linea in contenido.splitlines():
            linea_limpia = linea.strip().lower()
            if linea_limpia.startswith("open=") or linea_limpia.startswith("shellexecute="):
                objetivo = linea.split("=", 1)[1].strip()
                return f"autorun.inf esta configurado para ejecutar automaticamente: {objetivo}"
        return "autorun.inf presente en la raiz, pero sin una linea 'open=' reconocible."
    except (PermissionError, OSError):
        return "autorun.inf presente, pero no se pudo leer su contenido (permiso denegado)."


def escanear_usb(punto_montaje):
    """Analiza el CONTENIDO real del USB a pedido del usuario (boton
    'Analizar dispositivo'), no solo los nombres de archivo en la raiz:

    - Recorre todas las carpetas del dispositivo (no solo la raiz).
    - Lee el contenido de autorun.inf si existe, para decir a que
      ejecutable apunta en vez de solo confirmar que el archivo existe.
    - Abre los primeros bytes de cada archivo y compara su firma binaria
      real contra la extension que dice tener: si un archivo se llama
      'foto.jpg' pero arranca con la firma de un .exe, es un ejecutable
      disfrazado (tecnica comun de infeccion por USB), aunque el nombre
      diga otra cosa.
    - Compara nombres de archivo contra una lista de malware conocido.
    - Detecta doble extension (ej. 'foto.jpg.exe').

    Retorna {"sospechoso": bool, "hallazgos": [str, ...], "archivos_analizados": int}.
    """
    resultado = {"sospechoso": False, "hallazgos": [], "archivos_analizados": 0}
    if not punto_montaje or not os.path.exists(punto_montaje):
        resultado["hallazgos"].append("No se pudo acceder al dispositivo (¿sigue conectado?).")
        return resultado

    extensiones_ejecutables = {"exe", "scr", "bat", "cmd", "vbs", "js", "com"}

    try:
        ruta_autorun = os.path.join(punto_montaje, "autorun.inf")
        if os.path.exists(ruta_autorun):
            resultado["sospechoso"] = True
            resultado["hallazgos"].append(_analizar_autorun(ruta_autorun))

        contador = 0
        for raiz, carpetas, archivos in os.walk(punto_montaje):
            # Evita entrar en carpetas de sistema/basura que no aportan
            # nada al analisis y pueden ser muy pesadas.
            carpetas[:] = [c for c in carpetas if c.lower() not in
                           ("system volume information", "$recycle.bin")]
            for nombre in archivos:
                if contador >= _MAX_ARCHIVOS_ESCANEADOS:
                    resultado["hallazgos"].append(
                        f"Se alcanzo el limite de {_MAX_ARCHIVOS_ESCANEADOS} archivos analizados "
                        "(el dispositivo tiene mas contenido del que se revisa en un analisis rapido)."
                    )
                    resultado["archivos_analizados"] = contador
                    return resultado

                ruta = os.path.join(raiz, nombre)
                nombre_bajo = nombre.lower()
                contador += 1

                if nombre_bajo in MALWARE_CONOCIDO:
                    resultado["sospechoso"] = True
                    resultado["hallazgos"].append(f"Ejecutable conocido de malware: {ruta}")
                    continue

                partes = nombre_bajo.split(".")
                extension = partes[-1] if len(partes) > 1 else ""
                if len(partes) > 2 and extension in extensiones_ejecutables:
                    resultado["sospechoso"] = True
                    resultado["hallazgos"].append(f"Archivo con doble extension sospechosa: {ruta}")
                    continue

                # Chequeo de contenido real: la firma binaria no coincide
                # con lo que la extension del archivo promete.
                if extension in _EXTENSIONES_NO_EJECUTABLES:
                    firma = _leer_firma(ruta)
                    for marca, descripcion in _FIRMAS_EJECUTABLES.items():
                        if firma.startswith(marca):
                            resultado["sospechoso"] = True
                            resultado["hallazgos"].append(
                                f"'{nombre}' dice ser .{extension} pero su contenido real es un "
                                f"{descripcion} \u2014 posible ejecutable disfrazado."
                            )
                            break

        resultado["archivos_analizados"] = contador
        if not resultado["hallazgos"]:
            resultado["hallazgos"].append(
                f"Se analizaron {contador} archivo(s) y no se encontraron amenazas conocidas."
            )
    except PermissionError:
        resultado["hallazgos"].append("Permiso denegado al leer el dispositivo.")
    except Exception as e:
        resultado["hallazgos"].append(f"Error al analizar el dispositivo: {e}")

    return resultado


def expulsar_usb(punto_montaje, device=None):
    """Desmonta/expulsa el dispositivo de verdad (accion real, no
    simulada). Retorna (exito: bool, mensaje: str).

    - Windows: busca el verbo de "expulsar" dentro del menu contextual
      real de la unidad (Shell.Application) en vez de asumir que se
      llama "Eject". Ese nombre esta LOCALIZADO: en un Windows en
      espanol el verbo se llama "Expulsar", no "Eject", asi que pedir
      "Eject" a mano nunca lo encontraba. Ademas, InvokeVerb no lanza
      error si el verbo no existe: silenciosamente no hacia nada y el
      script igual terminaba con exito, por eso el boton "parecia"
      funcionar pero el USB nunca se desmontaba de verdad.
    - Linux: intenta primero con 'udisksctl unmount' (funciona sin sudo
      para medios montados por el propio usuario, que es el caso normal
      de un USB). Si no esta disponible, cae a 'umount' clasico, que
      puede pedir privilegios segun como se monto el dispositivo.
    """
    sistema = platform.system()
    try:
        if sistema == "Windows":
            letra = punto_montaje.rstrip("\\")
            # El script busca, entre los verbos reales del menu contextual
            # de la unidad, uno que coincida con expulsar/eject/extraer en
            # cualquier idioma de Windows, y recien ahi lo ejecuta. Si no
            # encuentra ninguno, lo dice explicitamente (exit 1) en vez de
            # terminar "exitosamente" sin haber hecho nada.
            script = (
                '$ErrorActionPreference = "Stop"; '
                f'$item = (New-Object -ComObject Shell.Application).Namespace(17).ParseName("{letra}"); '
                'if (-not $item) { Write-Error "No se encontro la unidad."; exit 1 }; '
                '$verbo = $item.Verbs() | Where-Object { '
                '$_.Name -match "Eject|Expulsar|Extraer|Quitar|Auswerfen|\u00c9jecter" '
                '} | Select-Object -First 1; '
                'if (-not $verbo) { Write-Error "No se encontro el comando de expulsar para esta unidad."; exit 1 }; '
                '$verbo.DoIt(); '
                'exit 0'
            )
            resultado = subprocess.run(
                ["powershell", "-NoProfile", "-Command", script],
                capture_output=True, text=True, timeout=15
            )
            if resultado.returncode == 0:
                return True, f"Dispositivo {letra} expulsado de forma segura."
            return False, (resultado.stderr or "No se pudo expulsar el dispositivo.").strip()

        # Linux / Mac
        if device and shutil.which("udisksctl"):
            resultado = subprocess.run(
                ["udisksctl", "unmount", "-b", device],
                capture_output=True, text=True, timeout=15
            )
            if resultado.returncode == 0:
                return True, f"Dispositivo {device} desmontado correctamente."
            # Si udisksctl fallo explicitamente (no por falta del comando),
            # se reporta ese error en vez de intentar umount a ciegas.
            if "not authorized" not in (resultado.stderr or "").lower():
                pass  # se intenta el respaldo de todas formas

        if shutil.which("umount"):
            resultado = subprocess.run(
                ["umount", punto_montaje],
                capture_output=True, text=True, timeout=15
            )
            if resultado.returncode == 0:
                return True, f"Dispositivo {punto_montaje} desmontado correctamente."
            return False, (resultado.stderr or
                            "No se pudo desmontar. Puede requerir permisos de administrador "
                            "o el dispositivo esta en uso.").strip()

        return False, "No se encontro una herramienta de desmontaje (udisksctl/umount) en este sistema."
    except FileNotFoundError:
        return False, "No se encontro la herramienta de desmontaje en este sistema."
    except subprocess.TimeoutExpired:
        return False, "La operacion tardo demasiado y fue cancelada."
    except Exception as e:
        return False, f"Error inesperado al intentar bloquear el dispositivo: {e}"


if __name__ == "__main__":
    # Prueba rapida por consola (sin interfaz grafica)
    estado = obtener_estado_sistema()
    print(json.dumps(estado, indent=4, ensure_ascii=False))
