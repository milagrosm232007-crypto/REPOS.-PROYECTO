import os
import time
import json
import importlib.util

# Configuración de la ruta para la importación dinámica del módulo backend
ruta_backend = os.path.join(os.getcwd(), "UNIFICADO.py")

try:
    spec = importlib.util.spec_from_file_location("UNIFICADO", ruta_backend)
    bk = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bk)
    print("[Integración] Módulo central 'UNIFICADO.py' acoplado con éxito.")
except Exception as e:
    print(f"[Error Crítico] No se pudo cargar el componente de backend: {e}")
    exit()

# Importación de la rutina de diagnóstico de rendimiento disponible
from pruebas.prueba_rendimiento import medir_velocidad_usb
from pruebas.generador_estres import iniciar_simulacion_comportamiento

def calcular_latencia_usb(ruta_usb):
    """Calcula la latencia de acceso I/O del dispositivo en milisegundos (ms)"""
    ruta_test = os.path.join(ruta_usb, "latencia_test.inf")
    tiempos = []
    
    try:
        # Realizamos 3 micro-operaciones de lectura/escritura para promediar la latencia de hardware
        for _ in range(3):
            t_inicio = time.perf_counter()
            with open(ruta_test, "w") as f:
                f.write("t")
            with open(ruta_test, "r") as f:
                _ = f.read()
            if os.path.exists(ruta_test):
                os.remove(ruta_test)
            t_fin = time.perf_counter()
            tiempos.append((t_fin - t_inicio) * 1000) # Conversión a milisegundos
            
        latencia_promedio = sum(tiempos) / len(tiempos)
        return round(latencia_promedio, 2)
    except Exception:
        return 0.0

if __name__ == "__main__":
    print("\n=======================================================")
    print("===   INICIANDO PRUEBA DE INTEGRACIÓN MEMORYGUARD   ===")
    print("=======================================================\n")
    
    # FASE 1: Pruebas de Carga y Estrés de Hardware
    print("[Fase 1] Inicializando Generador de Estrés en segundo plano...")
    iniciar_simulacion_comportamiento(duracion=12, ram_mb=200)
    
    print("[Fase 1] Telemetría en tiempo real a través del Subsistema de Monitoreo:")
    for i in range(3):
        time.sleep(4)
        try:
            estado = bk.obtener_estado_sistema()
            print(f"\n--- Métrica de Hardware #{i+1} (Bajo Carga Activa) ---")
            print(f"Consumo de CPU: {estado['cpu']}%")
            print(f"Consumo de RAM: {estado['ram']['uso_percent']}%")
        except AttributeError:
            print("[Aviso] La función 'obtener_estado_sistema' no está disponible en este entorno.")
            break
            
    print("\n[Fase 1] Simulación de estrés finalizada. Recursos del sistema liberados.")
    print("-------------------------------------------------------")
    
    # FASE 2: Detección y Análisis de Unidades Extraíbles (USB)
    print("[Fase 2] Escaneando puertos mediante el controlador de almacenamiento local...")
    
    try:
        usb_status = bk.detectar_usb()
        
        if usb_status and usb_status.get("usb_detectado"):
            unidad_real = usb_status["unidad"]
            print(f"Dispositivo detectado exitosamente en el punto de montaje: {unidad_real}")
            
            print("[Fase 2] Ejecutando pruebas avanzadas de rendimiento I/O (Lectura/Escritura)...")
            resultado_velocidad = medir_velocidad_usb(unidad_real, tamano_mb=10)
            
            print("[Fase 2] Calculando latencia promedio del controlador de almacenamiento...")
            latencia_ms = calcular_latencia_usb(unidad_real)
            print(f"Latencia promedio estimada: {latencia_ms} ms")
            
            print("\n=======================================================")
            print("===          REPORTE FINAL ESTRUCTURADO (JSON)       ===")
            print("=======================================================")
            
            # Extraemos la velocidad usando la llave exacta de tu diccionario de retorno
            velocidad_calculada = "N/A"
            if isinstance(resultado_velocidad, dict) and "velocidad_mb_s" in resultado_velocidad:
                velocidad_calculada = resultado_velocidad["velocidad_mb_s"]
            
            reporte_final = {
                "dispositivo_detectado": unidad_real,
                "rendimiento_dinamico_usb": {
                    "velocidad_transferencia_escritura_mb_s": velocidad_calculada,
                    "latencia_acceso_hardware_ms": latencia_ms
                }
            }
            print(json.dumps(reporte_final, indent=4))
        else:
            print("\n[Estatus] El controlador no identificó ningún dispositivo USB activo.")
            print("Verifique la conexión física de la unidad e intente nuevamente.")
    except Exception as e:
        print(f"\n[Error de Ejecución en Fase 2]: {e}")