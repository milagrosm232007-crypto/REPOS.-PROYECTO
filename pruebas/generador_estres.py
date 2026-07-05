import threading
import time

# Evento global de control: nos permite apagar los hilos en cualquier momento
evento_detener_estres = threading.Event()

def bucle_estres_cpu(duracion_segundos=15):
    print("[Rendimiento] Hilo de estrés de CPU iniciado.")
    tiempo_inicio = time.time()
    contador = 0
    
    # El bucle corre solo mientras no se active el evento de parada y no pase el tiempo límite
    while not evento_detener_estres.is_set():
        contador += 1
        if contador % 1000000 == 0:
            # Validamos si ya se cumplió el tiempo asignado
            if time.time() - tiempo_inicio >= duracion_segundos:
                break
                
    print("[Rendimiento] Estrés de CPU finalizado con éxito.")

def simular_consumo_ram(megabytes_a_consumir=250, duracion_segundos=15):
    print("[Rendimiento] Forzando consumo controlado de", megabytes_a_consumir, "MB de RAM...")
    
    try:
        # Reservamos la memoria de forma segura
        bloque_memoria = bytearray(megabytes_a_consumir * 1024 * 1024)
        
        tiempo_inicio = time.time()
        # Mantenemos la RAM ocupada de forma controlada sin congelar el hilo
        while not evento_detener_estres.is_set():
            if time.time() - tiempo_inicio >= duracion_segundos:
                break
            time.sleep(0.5)  # Respiro para el hilo
            
    except Exception as e:
        print("[Rendimiento] Error al reservar memoria:", str(e))
    finally:
        if 'bloque_memoria' in locals():
            del bloque_memoria
        print("[Rendimiento] Simulación terminada, RAM liberada.")

def iniciar_simulacion_comportamiento(duracion=15, ram_mb=200):
    """
    Función principal que llamarán tus compañeros desde el main.py o la GUI.
    Controla el tiempo de ejecución de las pruebas asíncronas.
    """
    # Reiniciamos el estado del evento de parada
    evento_detener_estres.clear()
    
    # Creamos los hilos pasando los argumentos de duración de forma unificada
    hilo_cpu = threading.Thread(
        target=bucle_estres_cpu, 
        args=(duracion,), 
        daemon=True
    )
    hilo_ram = threading.Thread(
        target=simular_consumo_ram, 
        args=(ram_mb, duracion), 
        daemon=True
    )
    
    hilo_cpu.start()
    hilo_ram.start()
    
    return {
        "status": "Simulación en progreso",
        "duracion_configurada": duracion,
        "ram_configurada_mb": ram_mb
    }

def detener_simulacion_inmediatamente():
    """
    ¡Función clave para la Interfaz! 
    Si el usuario presiona 'Detener' en la app, esto apaga los procesos al instante.
    """
    evento_detener_estres.set()
    print("[Rendimiento] Señal de parada enviada a los módulos de estrés.")

# Area de testeo local para verificar el comportamiento unificado
if __name__ == "__main__":
    print("Iniciando prueba unificada de estrés (Modo desarrollo)...")
    # Iniciamos una simulación de 5 segundos para probar
    iniciar_simulacion_comportamiento(duracion=5, ram_mb=100)
    
    # Esperamos el tiempo de ejecución
    time.sleep(6)
    print("Prueba local finalizada.")