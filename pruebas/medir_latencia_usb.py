import os
import time

def medir_latencia_usb(ruta_usb):
    """
    Mide el tiempo de respuesta inmediato (latencia) del hardware
    al realizar operaciones ultracortas de apertura y cierre.
    """
    print("Midiendo latencia de respuesta en:", ruta_usb)
    archivo_latencia = os.path.join(ruta_usb, "test_latencia.tmp")
    
    tiempos = []
    
    try:
        # Hacemos 5 micro-escrituras rapidas para promediar
        for _ in range(5):
            inicio = time.time()
            
            # Operacion ultra rapida: solo abrir y escribir 1 byte
            with open(archivo_latencia, "wb") as f:
                f.write(b"0")
                
            fin = time.time()
            tiempos.append(fin - inicio)
            time.sleep(0.1) # Pequeña pausa entre pruebas
            
        # Calcular el promedio en milisegundos (multiplicado por 1000)
        latencia_promedio_ms = (sum(tiempos) / len(tiempos)) * 1000
        
        print("Latencia media detectada:", round(latencia_promedio_ms, 2), "ms")
        
        return {
            "estado": "Exitoso",
            "latencia_ms": round(latencia_promedio_ms, 2),
            "calificacion": "Excelente" if latencia_promedio_ms < 15 else "Lenta"
        }
        
    except Exception as e:
        return {"estado": "Error", "detalle": str(e)}
        
    finally:
        if os.path.exists(archivo_latencia):
            os.remove(archivo_latencia)
