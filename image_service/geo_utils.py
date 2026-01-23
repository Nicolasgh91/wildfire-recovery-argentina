from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

def obtener_info_geografica(lat, lon):
    """
    Realiza Reverse Geocoding para obtener provincia, localidad y contexto.
    """
    geolocator = Nominatim(user_agent="wildfire_recovery_app_v1")
    
    try:
        # location devuelve un objeto con toda la dirección desglosada
        location = geolocator.reverse(f"{lat}, {lon}", language='es', exactly_one=True)
        
        if not location:
            return {}

        address = location.raw.get('address', {})
        display_name = location.address # Dirección completa legible

        datos = {
            'provincia': address.get('state', 'Desconocida'),
            'departamento': address.get('state_district', ''), # Partido/Departamento
            'localidad': address.get('town') or address.get('city') or address.get('village') or 'Zona Rural',
            'pais': address.get('country', 'Argentina'),
            'contexto_completo': display_name
        }

        # Detección simple de Áreas Protegidas en el nombre
        # (OpenStreetMap suele incluir "Parque Nacional" en el nombre del lugar)
        if "Parque Nacional" in display_name or "Reserva" in display_name:
            datos['area_protegida'] = True
            # Intentamos extraer el nombre del parque
            partes = display_name.split(',')
            for parte in partes:
                if "Parque" in parte or "Reserva" in parte:
                    datos['nombre_parque'] = parte.strip()
                    break
        else:
            datos['area_protegida'] = False
            datos['nombre_parque'] = "No detectado (Área privada o pública general)"

        return datos

    except Exception as e:
        print(f"⚠️ Error en geocoding: {e}")
        return {'localidad': 'Error de conexión', 'provincia': 'Desconocida'}