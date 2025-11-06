# -*- coding: utf-8 -*-
"""
Cliente de prueba para consumir el servicio FastAPI de clasificación de pólizas.
"""

import requests

# 🟢 URL del servidor FastAPI (ajústala si cambias el puerto)
BASE_URL = "http://127.0.0.1:8000"

# 🔥 Placa fija a consultar
placa = "NPL561"

def main():
    print(f"🚗 Consultando servicio para la placa {placa}...\n")

    try:
        response = requests.get(f"{BASE_URL}/clasificar/{placa}", timeout=20)

        if response.status_code == 200:
            data = response.json()
            print("✅ Respuesta exitosa:")
            for k, v in data.items():
                print(f"{k}: {v}")
        else:
            print(f"⚠️ Error HTTP {response.status_code}")
            print(response.text)

    except requests.RequestException as e:
        print(f"❌ Error al conectar con el servicio: {e}")

if __name__ == "__main__":
    main()
