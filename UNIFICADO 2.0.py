import psutil
import platform
import json
import os

PUERTOS_CONOCIDOS  = {
    21:"FTP", 22:"SSH", 23:"Telnet", 80:"HTTP", 135:"RPC",
    139:"NetBIOS", 443:"HTTPS", 445:"SMB", 3389:"RDP", 5900:"VNC"
}
PUERTOS_RIESGO    = {21, 23, 135, 139, 445, 3389, 5900}
RUTAS_SOSPECHOSAS = ["\\temp\\", "\\appdata\\roaming\\",
                      "\\appdata\\local\\temp\\", "\\users\\public\\"]
MALWARE_CONOCIDO  = {"mimikatz.exe", "nc.exe", "ncat.exe",
                      "netcat.exe", "psexec.exe", "wce.exe", "pwdump.exe"}


def obtener_cpu():
    return psutil.cpu_percent(interval=1)

def obtener_ram():
    memoria = psutil.virtual_memory()
    return {
        "uso_percent": memoria.percent,
        "total_gb": round(memoria.total / (1024**3), 2),
        "disponible_gb": round(memoria.available / (1024**3), 2)
    }

def obtener_sistema():
    return {
        "sistema": platform.system(),
        "version": platform.release(),
        "equipo": platform.node(),
        "arquitectura": platform.machine()
    }

def obtener_disco():
    disco = psutil.disk_usage("C:\\")
    return {
        "unidad": "C:",
        "total_gb": round(disco.total / (1024**3), 2),
        "usado_gb": round(disco.used / (1024**3), 2),
        "libre_gb": round(disco.free / (1024**3), 2),
        "porcentaje": disco.percent
    }

def detectar_usb():
    """Retorna un diccionario con el estado del hardware USB"""
    particiones = psutil.disk_partitions()
    for particion in particiones:
        if "removable" in particion.opts:
            return {
                "usb_detectado": True,
                "unidad": particion.device
            }
    return {
        "usb_detectado": False,
        "unidad": None
    }

def obtener_info_usb(unidad):
    uso = psutil.disk_usage(unidad)
    return {
        "unidad": unidad,
        "total_gb": round(uso.total / (1024**3), 2),
        "usado_gb": round(uso.used / (1024**3), 2),
        "libre_gb": round(uso.free / (1024**3), 2),
        "porcentaje": uso.percent
    }

def obtener_procesos():
    procesos = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
        try:
            procesos.append({
                "pid": proc.info['pid'],
                "nombre": proc.info['name'],
                "cpu": proc.info['cpu_percent']
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return procesos[:10]

#Ciber
def detectar_puertos():
    alertas = []
    try:
        for c in psutil.net_connections(kind="inet"):
            if c.status == "LISTEN" and c.laddr.port in PUERTOS_RIESGO:
                p = c.laddr.port
                alertas.append(("ALTO", f"Puerto {p} ({PUERTOS_CONOCIDOS[p]}) expuesto en LISTEN"))
    except psutil.AccessDenied:
        alertas.append(("INFO", "Ejecutar como Administrador para ver puertos"))
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
                alertas.append(("MEDIO", f"Conexion externa sospechosa: {ip}:{puerto} - puerto no estandar"))
    except psutil.AccessDenied:
        alertas.append(("INFO", "Ejecutar como Administrador para ver conexiones"))
    return alertas

def detectar_procesos():
    alertas = []
    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        try:
            nombre = (proc.info['name'] or "").lower()
            ruta   = (proc.info['exe']  or "").lower()
            if nombre in MALWARE_CONOCIDO:
                alertas.append(("ALTO", f"PID {proc.info['pid']} - herramienta ofensiva detectada: {proc.info['name']}"))
            elif any(rs in ruta for rs in RUTAS_SOSPECHOSAS):
                alertas.append(("MEDIO", f"PID {proc.info['pid']} ({proc.info['name']}) ejecutando desde ruta sospechosa"))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return alertas

def auditar_seguridad_usb(punto_montaje):
    """Analiza la seguridad del USB si hay uno conectado"""
    alertas = []
    if not punto_montaje:
        return alertas
        
    try:
        ruta_autorun = os.path.join(punto_montaje, "autorun.inf")
        if os.path.exists(ruta_autorun):
            alertas.append((
                "ALTO", 
                f"Dispositivo USB en {punto_montaje} - ¡Amenaza detectada: archivo autorun.inf sospechoso!"
            ))
        else:
            alertas.append((
                "INFO", 
                f"Dispositivo USB en {punto_montaje} conectado - Seguro (Sin amenazas detectadas)"
            ))
    except Exception as e:
        alertas.append(("INFO", f"Error al monitorear seguridad de USB: {str(e)}"))
    return alertas


def obtener_estado_sistema():
    disco = obtener_disco()
    usb = detectar_usb() 
    ram = obtener_ram()
    cpu = obtener_cpu()
    sistema = obtener_sistema()
    procesos = obtener_procesos()

    resultado = {
        "cpu": cpu,
        "ram": ram,
        "disco": disco,
        "usb": usb,
        "procesos": {
            "cantidad": len(procesos),
            "lista": procesos
        },
        "sistema": sistema
    }

    if usb["usb_detectado"]:
        resultado["info_usb"] = obtener_info_usb(usb["unidad"])

    return resultado

def mostrar_alertas():
    # Obtener el estado del USB primero para auditarlo
    usb = detectar_usb()
    unidad_usb = usb["unidad"] if usb["usb_detectado"] else None

    # Unificar alertas usando nombres únicos
    alertas = detectar_puertos() + detectar_conexiones() + detectar_procesos() + auditar_seguridad_usb(unidad_usb)
    alertas.sort(key=lambda a: {"ALTO": 0, "MEDIO": 1, "INFO": 2}[a[0]])

    ICONO  = {"ALTO": "[!!]", "MEDIO": "[!] ", "INFO": "[i] "}
    conteo = {n: sum(1 for a in alertas if a[0] == n) for n in ("ALTO", "MEDIO", "INFO")}

    print("=" * 55)
    print("  DETECCION DE SEGURIDAD - Windows (MemGuard Backend)")
    print(f"  ALTO: {conteo['ALTO']}  MEDIO: {conteo['MEDIO']}  INFO: {conteo['INFO']}")
    print("=" * 55)
    if not alertas:
        print("  [OK] Sin alertas detectadas.")
    for nivel, msg in alertas:
        print(f"  {ICONO[nivel]} [{nivel:5}] {msg}")

if __name__ == "__main__":
    estado = obtener_estado_sistema()
    print("========== MONITOREO DEL SISTEMA ==========")
    print(json.dumps(estado, indent=4))
    print("\n")
    mostrar_alertas()
