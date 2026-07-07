import os
import time

def medir_velocidad_usb(ruta_usb, tamano_mb=50):
    print("Iniciando prueba de rendimiento I/O en:", ruta_usb)
    
    ruta_origen = "archivo_temporal.tmp"
    ruta_destino = os.path.join(ruta_usb, "prueba_memguard.tmp")
    
    # Bloque modular de 1 MB para proteger la medicion de RAM del backend
    bloque_un_mb = b"0" * (1024 * 1024)
    
    try:
        # 1. Crear el archivo de prueba de forma progresiva
        with open(ruta_origen, "wb") as f:
            for _ in range(tamano_mb):
                f.write(bloque_un_mb)
                
        # 2. Medir el tiempo de escritura real hacia el USB
        tiempo_inicio = time.time()
        with open(ruta_destino, "wb") as f:
            for _ in range(tamano_mb):
                f.write(bloque_un_mb)
        tiempo_fin = time.time()
        
        tiempo_total = tiempo_fin - tiempo_inicio
        velocidad = tamano_mb / tiempo_total if tiempo_total > 0 else 0
        
        print("Escritura completada en:", round(tiempo_total, 2), "segundos.")
        print("Velocidad de transferencia calculada:", round(velocidad, 2), "MB/s")
        
        # Devolvemos los datos estructurados para la integracion total del programa
        return {
            "estado": "Exitoso",
            "tiempo_segundos": round(tiempo_total, 2),
            "velocidad_mb_s": round(velocidad, 2)
        }
        
    except Exception as e:
        return {
            "estado": "Error",
            "detalle": str(e)
        }
        
    finally:
        # Limpieza automatica del almacenamiento
        if os.path.exists(ruta_origen):
            os.remove(ruta_origen)
        if os.path.exists(ruta_destino):
            os.remove(ruta_destino)

if __name__ == "__main__":
    # Prueba el script en tu carpeta local asignando el punto "."
    resultado = medir_velocidad_usb(".", tamano_mb=10)
