"""
Conexión y operaciones con Supabase/PostgreSQL
"""
from supabase import create_client, Client
from typing import Dict, List, Optional
from datetime import datetime
from api.config import settings


class Database:
    """Cliente para operaciones con Supabase"""
    
    def __init__(self):
        """Inicializa conexión a Supabase"""
        self.client: Client = create_client(
            settings.supabase_url,
            settings.supabase_service_key  # Usamos service_key para bypass RLS
        )
    
    # ========== OPERACIONES: INCENDIOS ==========
    
    def crear_incendio(self, incendio_data: Dict) -> Dict:
        """
        Crea un nuevo registro de incendio
        
        Args:
            incendio_data: Dict con los datos del incendio
            
        Returns:
            Incendio creado con ID
        """
        response = self.client.table('incendios').insert(incendio_data).execute()
        return response.data[0] if response.data else None
    
    def obtener_incendio(self, incendio_id: str) -> Optional[Dict]:
        """
        Obtiene un incendio por ID
        
        Args:
            incendio_id: UUID del incendio
            
        Returns:
            Dict con datos del incendio o None
        """
        response = self.client.table('incendios') \
            .select('*') \
            .eq('id', incendio_id) \
            .execute()
        
        return response.data[0] if response.data else None
    
    def listar_incendios(
        self,
        provincia: Optional[str] = None,
        fecha_inicio: Optional[str] = None,
        fecha_fin: Optional[str] = None,
        tipo: Optional[str] = None,
        limite: int = 100
    ) -> List[Dict]:
        """
        Lista incendios con filtros opcionales
        
        Args:
            provincia: Filtrar por provincia
            fecha_inicio: Fecha mínima (YYYY-MM-DD)
            fecha_fin: Fecha máxima (YYYY-MM-DD)
            tipo: 'nuevo' o 'recurrente'
            limite: Máximo número de resultados
            
        Returns:
            Lista de incendios
        """
        query = self.client.table('incendios').select('*')
        
        if provincia:
            query = query.eq('provincia', provincia)
        
        if fecha_inicio:
            query = query.gte('fecha_deteccion', fecha_inicio)
        
        if fecha_fin:
            query = query.lte('fecha_deteccion', fecha_fin)
        
        if tipo:
            query = query.eq('tipo', tipo)
        
        query = query.limit(limite).order('fecha_deteccion', desc=True)
        
        response = query.execute()
        return response.data
    
    def actualizar_estado_incendio(
        self,
        incendio_id: str,
        estado: str,
        error_mensaje: Optional[str] = None
    ) -> Dict:
        """
        Actualiza el estado de análisis de un incendio
        
        Args:
            incendio_id: UUID del incendio
            estado: 'pendiente' | 'procesando' | 'completado' | 'error'
            error_mensaje: Mensaje de error si estado='error'
            
        Returns:
            Incendio actualizado
        """
        update_data = {'estado_analisis': estado}
        
        if error_mensaje:
            update_data['error_mensaje'] = error_mensaje
        
        response = self.client.table('incendios') \
            .update(update_data) \
            .eq('id', incendio_id) \
            .execute()
        
        return response.data[0] if response.data else None
    
    # ========== OPERACIONES: ANÁLISIS MENSUAL ==========
    
    def crear_analisis_mensual(self, analisis_data: Dict) -> Dict:
        """
        Crea un registro de análisis mensual
        
        Args:
            analisis_data: Dict con datos del análisis
            
        Returns:
            Análisis creado
        """
        response = self.client.table('analisis_mensual') \
            .insert(analisis_data) \
            .execute()
        
        return response.data[0] if response.data else None
    
    def obtener_analisis_incendio(self, incendio_id: str) -> List[Dict]:
        """
        Obtiene todos los análisis mensuales de un incendio
        
        Args:
            incendio_id: UUID del incendio
            
        Returns:
            Lista de análisis ordenados por mes
        """
        response = self.client.table('analisis_mensual') \
            .select('*') \
            .eq('incendio_id', incendio_id) \
            .order('mes_numero') \
            .execute()
        
        return response.data
    
    def obtener_analisis_mes(
        self,
        incendio_id: str,
        mes_numero: int
    ) -> Optional[Dict]:
        """
        Obtiene el análisis de un mes específico
        
        Args:
            incendio_id: UUID del incendio
            mes_numero: Número de mes (1-36)
            
        Returns:
            Análisis del mes o None
        """
        response = self.client.table('analisis_mensual') \
            .select('*') \
            .eq('incendio_id', incendio_id) \
            .eq('mes_numero', mes_numero) \
            .execute()
        
        return response.data[0] if response.data else None
    
    # ========== OPERACIONES: SUPERPOSICIONES ==========
    
    def obtener_superposiciones_incendio(
        self,
        incendio_id: str
    ) -> List[Dict]:
        """
        Obtiene todas las superposiciones de un incendio
        
        Args:
            incendio_id: UUID del incendio
            
        Returns:
            Lista de superposiciones
        """
        # Buscar donde el incendio es A o B
        response_a = self.client.table('superposiciones') \
            .select('*') \
            .eq('incendio_a_id', incendio_id) \
            .execute()
        
        response_b = self.client.table('superposiciones') \
            .select('*') \
            .eq('incendio_b_id', incendio_id) \
            .execute()
        
        # Combinar resultados
        superposiciones = response_a.data + response_b.data
        
        return superposiciones
    
    # ========== ESTADÍSTICAS ==========
    
    def estadisticas_generales(self) -> Dict:
        """
        Obtiene estadísticas generales del sistema
        
        Returns:
            Dict con estadísticas
        """
        # Total de incendios
        total = self.client.table('incendios') \
            .select('id', count='exact') \
            .execute()
        
        # Incendios recurrentes
        recurrentes = self.client.table('incendios') \
            .select('id', count='exact') \
            .eq('tipo', 'recurrente') \
            .execute()
        
        # Incendios completados
        completados = self.client.table('incendios') \
            .select('id', count='exact') \
            .eq('estado_analisis', 'completado') \
            .execute()
        
        return {
            'total_incendios': total.count,
            'incendios_recurrentes': recurrentes.count,
            'analisis_completados': completados.count,
            'porcentaje_completado': round(
                (completados.count / total.count * 100) if total.count > 0 else 0,
                2
            )
        }
    
    def test_connection(self) -> Dict:
        """
        Prueba la conexión a Supabase
        
        Returns:
            Dict con resultado del test
        """
        try:
            # Intentar hacer una query simple
            response = self.client.table('incendios') \
                .select('id', count='exact') \
                .limit(1) \
                .execute()
            
            return {
                'status': 'success',
                'message': 'Conexión exitosa a Supabase',
                'total_incendios': response.count
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }


# Instancia global (singleton)
db = Database()


if __name__ == '__main__':
    print("=== Probando conexión a Supabase ===\n")
    
    # Test de conexión
    resultado = db.test_connection()
    print(f"Status: {resultado['status']}")
    print(f"Mensaje: {resultado['message']}")
    
    if resultado['status'] == 'success':
        print(f"Total incendios en BD: {resultado['total_incendios']}")
        
        # Estadísticas generales
        print("\n=== Estadísticas Generales ===")
        stats = db.estadisticas_generales()
        for key, value in stats.items():
            print(f"{key}: {value}")