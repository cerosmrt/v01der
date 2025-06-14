import sounddevice as sd

def encontrar_dispositivo_salida(preferido_nombre="H Series", fallback_nombre="Speakers (Realtek(R) Audio)"):
    devices = sd.query_devices()
    salida_idx = None
    fallback_idx = None
    
    for idx, dev in enumerate(devices):
        if dev['max_output_channels'] > 0:
            nombre = dev['name']
            if preferido_nombre in nombre:
                salida_idx = idx
                break  # Encontramos el preferido, no seguimos buscando
            if fallback_nombre in nombre:
                fallback_idx = idx
    
    if salida_idx is not None:
        print(f"Usando salida preferida: {devices[salida_idx]['name']}")
        return salida_idx
    elif fallback_idx is not None:
        print(f"No se encontró salida preferida, usando fallback: {devices[fallback_idx]['name']}")
        return fallback_idx
    else:
        raise RuntimeError("No se encontró dispositivo de salida válido")

# Ejemplo de uso
dispositivo_salida = encontrar_dispositivo_salida()

# Aquí podés usar `dispositivo_salida` para reproducir audio con sounddevice o para configurar en tu app
print(f"ID del dispositivo de salida a usar: {dispositivo_salida}")
