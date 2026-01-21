# Image Service - Google Earth Engine Client

Servicio para interactuar con Google Earth Engine y obtener imágenes satelitales.

## Configuración

1. Asegúrate de tener el entorno virtual activado o usa el Python del venv directamente.

2. Configura la variable de entorno `GEE_PRIVATE_KEY_PATH` apuntando al archivo de credenciales:
   ```bash
   # En Windows PowerShell
   $env:GEE_PRIVATE_KEY_PATH="C:\ruta\a\tu\gee-service-account.json"
   
   # O crea un archivo .env en la raíz del proyecto con:
   GEE_PRIVATE_KEY_PATH=./gee-service-account.json
   ```

## Ejecutar el script

**Opción 1: Usando el Python del venv directamente (recomendado)**
```bash
# Desde la raíz del proyecto
.\venv\Scripts\python.exe image-service\gee_client.py
```

**Opción 2: Activando el entorno virtual primero**
```bash
# Activar el venv
.\venv\Scripts\Activate.ps1

# Ejecutar el script
python image-service\gee_client.py
```

## Solución de problemas

Si obtienes `ModuleNotFoundError: No module named 'ee'`:
- Asegúrate de estar usando el Python del entorno virtual
- Verifica que `earthengine-api` esté instalado: `.\venv\Scripts\python.exe -m pip list | Select-String earthengine`
