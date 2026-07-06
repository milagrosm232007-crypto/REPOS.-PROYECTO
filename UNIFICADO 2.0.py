import psutil
import platform
import json

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

if __name__ == "__main__":
    estado = obtener_estado_sistema()
    print("========== MONITOREO DEL SISTEMA ==========")
    print(json.dumps(estado, indent=4))
