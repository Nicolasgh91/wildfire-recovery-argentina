"""
Storage Service para ForestGuard - Cloudflare R2.

Este módulo proporciona acceso a Cloudflare R2 para almacenar:
- Thumbnails de imágenes satelitales
- PDFs de reportes y certificados
- Imágenes HD para descarga

Límites Free Tier:
    - 10 GB storage
    - 1M Class A ops/mes (escrituras)
    - 10M Class B ops/mes (lecturas)
    - Egreso: ILIMITADO

Autor: ForestGuard Dev Team
Versión: 1.0.0
"""

import boto3
import hashlib
import logging
from io import BytesIO
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, BinaryIO, Union, List
from dataclasses import dataclass
import mimetypes

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURACIÓN
# =============================================================================

# Buckets predefinidos
BUCKETS = {
    "images": "forestguard-images",      # Thumbnails, visualizaciones
    "reports": "forestguard-reports",    # PDFs de reportes
    "certificates": "forestguard-certificates",  # Certificados legales
}

# Prefijos de organización
PREFIXES = {
    "thumbnails": "thumbnails/",
    "hd_images": "hd/",
    "ndvi": "ndvi/",
    "temporal_series": "series/",
    "reports": "reports/",
    "certificates": "certs/",
}

# TTL para URLs presignadas (segundos)
DEFAULT_URL_EXPIRY = 3600  # 1 hora
EXTENDED_URL_EXPIRY = 86400  # 24 horas


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class UploadResult:
    """Resultado de una operación de upload."""
    success: bool
    key: str
    url: str
    size_bytes: int
    content_hash: str
    error: Optional[str] = None

@dataclass
class StorageStats:
    """Estadísticas de uso de storage."""
    total_objects: int
    total_size_bytes: int
    total_size_mb: float
    by_prefix: Dict[str, int]


# =============================================================================
# EXCEPCIONES
# =============================================================================

class StorageError(Exception):
    """Error base de storage."""
    pass

class StorageUploadError(StorageError):
    """Error al subir archivo."""
    pass

class StorageNotFoundError(StorageError):
    """Archivo no encontrado."""
    pass


# =============================================================================
# SERVICIO PRINCIPAL
# =============================================================================

class StorageService:
    """
    Servicio de almacenamiento usando Cloudflare R2.
    
    R2 es compatible con S3 API, por lo que usamos boto3.
    
    Ejemplo de uso:
        storage = StorageService(
            access_key="...",
            secret_key="...",
            endpoint_url="https://xxx.r2.cloudflarestorage.com"
        )
        
        # Subir thumbnail
        result = storage.upload_thumbnail(
            fire_event_id="uuid-123",
            image_bytes=png_bytes,
            vis_type="RGB",
            acquisition_date=date(2023, 6, 15)
        )
        
        # Obtener URL
        url = storage.get_signed_url(result.key)
    """
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(
        self,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        default_bucket: str = "forestguard-images"
    ):
        """
        Inicializa el servicio de storage.
        
        Args:
            access_key: R2 Access Key ID
            secret_key: R2 Secret Access Key
            endpoint_url: R2 endpoint (https://xxx.r2.cloudflarestorage.com)
            default_bucket: Bucket por defecto
        """
        if self._initialized:
            return
            
        self._access_key = access_key
        self._secret_key = secret_key
        self._endpoint_url = endpoint_url
        self._default_bucket = default_bucket
        self._client = None
    
    def _get_client(self):
        """Obtiene o crea el cliente S3/R2."""
        if self._client is None:
            import os
            
            access_key = self._access_key or os.environ.get("R2_ACCESS_KEY_ID")
            secret_key = self._secret_key or os.environ.get("R2_SECRET_ACCESS_KEY")
            endpoint = self._endpoint_url or os.environ.get("R2_ENDPOINT_URL")
            
            if not all([access_key, secret_key, endpoint]):
                raise StorageError(
                    "Faltan credenciales R2. Configurar R2_ACCESS_KEY_ID, "
                    "R2_SECRET_ACCESS_KEY y R2_ENDPOINT_URL"
                )
            
            self._client = boto3.client(
                "s3",
                endpoint_url=endpoint,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name="auto"  # R2 usa 'auto'
            )
            self._initialized = True
        
        return self._client
    
    # =========================================================================
    # MÉTODOS DE UPLOAD
    # =========================================================================
    
    def upload_bytes(
        self,
        data: bytes,
        key: str,
        bucket: Optional[str] = None,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> UploadResult:
        """
        Sube bytes a R2.
        
        Args:
            data: Contenido a subir
            key: Key (path) en el bucket
            bucket: Bucket destino (default: forestguard-images)
            content_type: MIME type (se infiere si no se proporciona)
            metadata: Metadata adicional
            
        Returns:
            UploadResult con detalles de la operación
        """
        client = self._get_client()
        bucket = bucket or self._default_bucket
        
        # Inferir content type
        if not content_type:
            content_type = mimetypes.guess_type(key)[0] or "application/octet-stream"
        
        # Calcular hash
        content_hash = hashlib.sha256(data).hexdigest()
        
        try:
            extra_args = {
                "ContentType": content_type,
            }
            if metadata:
                extra_args["Metadata"] = metadata
            
            client.put_object(
                Bucket=bucket,
                Key=key,
                Body=data,
                **extra_args
            )
            
            # Generar URL pública (si el bucket es público) o presignada
            url = self.get_public_url(key, bucket)
            
            logger.info(f"Uploaded {len(data)} bytes to {bucket}/{key}")
            
            return UploadResult(
                success=True,
                key=key,
                url=url,
                size_bytes=len(data),
                content_hash=content_hash
            )
            
        except Exception as e:
            logger.error(f"Error uploading to {bucket}/{key}: {e}")
            return UploadResult(
                success=False,
                key=key,
                url="",
                size_bytes=0,
                content_hash="",
                error=str(e)
            )
    
    def upload_file(
        self,
        file_path: Union[str, Path],
        key: Optional[str] = None,
        bucket: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> UploadResult:
        """
        Sube un archivo local a R2.
        
        Args:
            file_path: Ruta al archivo local
            key: Key en R2 (default: nombre del archivo)
            bucket: Bucket destino
            metadata: Metadata adicional
            
        Returns:
            UploadResult
        """
        path = Path(file_path)
        key = key or path.name
        
        with open(path, "rb") as f:
            data = f.read()
        
        content_type = mimetypes.guess_type(str(path))[0]
        
        return self.upload_bytes(
            data=data,
            key=key,
            bucket=bucket,
            content_type=content_type,
            metadata=metadata
        )
    
    def upload_thumbnail(
        self,
        fire_event_id: str,
        image_bytes: bytes,
        vis_type: str = "RGB",
        acquisition_date: Optional[Any] = None,
        format: str = "png"
    ) -> UploadResult:
        """
        Sube un thumbnail de imagen satelital.
        
        Organiza los archivos por fire_event_id y tipo de visualización.
        
        Args:
            fire_event_id: ID del evento de incendio
            image_bytes: Contenido de la imagen
            vis_type: Tipo de visualización (RGB, NDVI, FALSE_COLOR)
            acquisition_date: Fecha de adquisición
            format: Formato de imagen
            
        Returns:
            UploadResult
        """
        # Construir key organizado
        date_str = ""
        if acquisition_date:
            if hasattr(acquisition_date, 'strftime'):
                date_str = acquisition_date.strftime("%Y%m%d")
            else:
                date_str = str(acquisition_date).replace("-", "")
        
        key = f"{PREFIXES['thumbnails']}{fire_event_id}/{vis_type}_{date_str}.{format}"
        
        metadata = {
            "fire_event_id": fire_event_id,
            "vis_type": vis_type,
            "acquisition_date": date_str,
        }
        
        return self.upload_bytes(
            data=image_bytes,
            key=key,
            bucket=BUCKETS["images"],
            content_type=f"image/{format}",
            metadata=metadata
        )
    
    def upload_temporal_series(
        self,
        fire_event_id: str,
        images: Dict[str, bytes],
        vis_type: str = "RGB"
    ) -> Dict[str, UploadResult]:
        """
        Sube una serie temporal de imágenes.
        
        Args:
            fire_event_id: ID del evento
            images: Dict de {fecha_str: bytes}
            vis_type: Tipo de visualización
            
        Returns:
            Dict de {fecha_str: UploadResult}
        """
        results = {}
        
        for date_str, image_bytes in images.items():
            key = f"{PREFIXES['temporal_series']}{fire_event_id}/{vis_type}_{date_str}.png"
            
            result = self.upload_bytes(
                data=image_bytes,
                key=key,
                bucket=BUCKETS["images"],
                content_type="image/png",
                metadata={
                    "fire_event_id": fire_event_id,
                    "vis_type": vis_type,
                    "date": date_str,
                    "series": "true"
                }
            )
            results[date_str] = result
        
        return results
    
    def upload_report_pdf(
        self,
        report_id: str,
        pdf_bytes: bytes,
        report_type: str = "historical"
    ) -> UploadResult:
        """
        Sube un PDF de reporte.
        
        Args:
            report_id: ID único del reporte
            pdf_bytes: Contenido del PDF
            report_type: Tipo de reporte (historical, judicial, etc.)
            
        Returns:
            UploadResult
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        key = f"{PREFIXES['reports']}{report_type}/{report_id}_{timestamp}.pdf"
        
        return self.upload_bytes(
            data=pdf_bytes,
            key=key,
            bucket=BUCKETS["reports"],
            content_type="application/pdf",
            metadata={
                "report_id": report_id,
                "report_type": report_type,
                "generated_at": timestamp
            }
        )
    
    # =========================================================================
    # MÉTODOS DE DESCARGA Y URLS
    # =========================================================================
    
    def get_signed_url(
        self,
        key: str,
        bucket: Optional[str] = None,
        expiry_seconds: int = DEFAULT_URL_EXPIRY
    ) -> str:
        """
        Genera URL presignada para acceso temporal.
        
        Args:
            key: Key del objeto
            bucket: Bucket
            expiry_seconds: Tiempo de validez
            
        Returns:
            URL presignada
        """
        client = self._get_client()
        bucket = bucket or self._default_bucket
        
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expiry_seconds
        )
        
        return url
    
    def get_public_url(self, key: str, bucket: Optional[str] = None) -> str:
        """
        Genera URL pública (asume bucket con acceso público).
        
        Para R2 con custom domain configurado.
        
        Args:
            key: Key del objeto
            bucket: Bucket
            
        Returns:
            URL pública
        """
        import os
        
        bucket = bucket or self._default_bucket
        public_url_base = os.environ.get("R2_PUBLIC_URL", "")
        
        if public_url_base:
            return f"{public_url_base.rstrip('/')}/{key}"
        else:
            # Fallback a presigned URL
            return self.get_signed_url(key, bucket)
    
    def download_bytes(self, key: str, bucket: Optional[str] = None) -> bytes:
        """
        Descarga un objeto como bytes.
        
        Args:
            key: Key del objeto
            bucket: Bucket
            
        Returns:
            Contenido como bytes
        """
        client = self._get_client()
        bucket = bucket or self._default_bucket
        
        try:
            response = client.get_object(Bucket=bucket, Key=key)
            return response["Body"].read()
        except client.exceptions.NoSuchKey:
            raise StorageNotFoundError(f"Objeto no encontrado: {bucket}/{key}")
    
    def exists(self, key: str, bucket: Optional[str] = None) -> bool:
        """Verifica si un objeto existe."""
        client = self._get_client()
        bucket = bucket or self._default_bucket
        
        try:
            client.head_object(Bucket=bucket, Key=key)
            return True
        except:
            return False
    
    # =========================================================================
    # MÉTODOS DE LISTADO Y ESTADÍSTICAS
    # =========================================================================
    
    def list_objects(
        self,
        prefix: str = "",
        bucket: Optional[str] = None,
        max_keys: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Lista objetos en un bucket/prefix.
        
        Args:
            prefix: Prefijo para filtrar
            bucket: Bucket
            max_keys: Máximo número de resultados
            
        Returns:
            Lista de dicts con {key, size, last_modified}
        """
        client = self._get_client()
        bucket = bucket or self._default_bucket
        
        response = client.list_objects_v2(
            Bucket=bucket,
            Prefix=prefix,
            MaxKeys=max_keys
        )
        
        objects = []
        for obj in response.get("Contents", []):
            objects.append({
                "key": obj["Key"],
                "size": obj["Size"],
                "last_modified": obj["LastModified"],
            })
        
        return objects
    
    def get_fire_event_images(self, fire_event_id: str) -> List[Dict[str, Any]]:
        """
        Obtiene todas las imágenes asociadas a un evento de incendio.
        
        Args:
            fire_event_id: ID del evento
            
        Returns:
            Lista de objetos con metadata
        """
        # Buscar en thumbnails y series
        thumbnails = self.list_objects(
            prefix=f"{PREFIXES['thumbnails']}{fire_event_id}/",
            bucket=BUCKETS["images"]
        )
        
        series = self.list_objects(
            prefix=f"{PREFIXES['temporal_series']}{fire_event_id}/",
            bucket=BUCKETS["images"]
        )
        
        return thumbnails + series
    
    def get_storage_stats(self, bucket: Optional[str] = None) -> StorageStats:
        """
        Obtiene estadísticas de uso del storage.
        
        Args:
            bucket: Bucket a analizar (default: images)
            
        Returns:
            StorageStats con totales y desglose por prefijo
        """
        client = self._get_client()
        bucket = bucket or self._default_bucket
        
        total_objects = 0
        total_size = 0
        by_prefix = {}
        
        # Iterar por cada prefijo conocido
        for prefix_name, prefix_value in PREFIXES.items():
            objects = self.list_objects(prefix=prefix_value, bucket=bucket)
            count = len(objects)
            size = sum(obj["size"] for obj in objects)
            
            by_prefix[prefix_name] = count
            total_objects += count
            total_size += size
        
        return StorageStats(
            total_objects=total_objects,
            total_size_bytes=total_size,
            total_size_mb=round(total_size / (1024 * 1024), 2),
            by_prefix=by_prefix
        )
    
    # =========================================================================
    # MÉTODOS DE LIMPIEZA
    # =========================================================================
    
    def delete_object(self, key: str, bucket: Optional[str] = None) -> bool:
        """
        Elimina un objeto.
        
        Args:
            key: Key del objeto
            bucket: Bucket
            
        Returns:
            True si se eliminó exitosamente
        """
        client = self._get_client()
        bucket = bucket or self._default_bucket
        
        try:
            client.delete_object(Bucket=bucket, Key=key)
            logger.info(f"Deleted {bucket}/{key}")
            return True
        except Exception as e:
            logger.error(f"Error deleting {bucket}/{key}: {e}")
            return False
    
    def cleanup_old_objects(
        self,
        prefix: str,
        days_old: int = 30,
        bucket: Optional[str] = None,
        dry_run: bool = True
    ) -> List[str]:
        """
        Elimina objetos más antiguos que N días.
        
        Args:
            prefix: Prefijo a limpiar
            days_old: Antigüedad mínima para eliminar
            bucket: Bucket
            dry_run: Si True, solo reporta sin eliminar
            
        Returns:
            Lista de keys eliminados (o que se eliminarían)
        """
        objects = self.list_objects(prefix=prefix, bucket=bucket)
        cutoff = datetime.now() - timedelta(days=days_old)
        
        to_delete = []
        for obj in objects:
            if obj["last_modified"].replace(tzinfo=None) < cutoff:
                to_delete.append(obj["key"])
        
        if not dry_run:
            for key in to_delete:
                self.delete_object(key, bucket)
        
        action = "Would delete" if dry_run else "Deleted"
        logger.info(f"{action} {len(to_delete)} objects older than {days_old} days")
        
        return to_delete
    
    # =========================================================================
    # HEALTH CHECK
    # =========================================================================
    
    def health_check(self) -> Dict[str, Any]:
        """
        Verifica el estado de la conexión con R2.
        
        Returns:
            Dict con status y detalles
        """
        try:
            client = self._get_client()
            
            # Verificar acceso al bucket principal
            client.head_bucket(Bucket=self._default_bucket)
            
            # Obtener stats básicas
            objects = self.list_objects(max_keys=10)
            
            return {
                "status": "healthy",
                "bucket": self._default_bucket,
                "accessible": True,
                "sample_objects": len(objects)
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "bucket": self._default_bucket,
                "accessible": False,
                "error": str(e)
            }


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def get_storage_service() -> StorageService:
    """
    Factory function para obtener instancia de StorageService.
    
    Usar como dependency injection en FastAPI:
        @router.post("/upload")
        def upload(storage: StorageService = Depends(get_storage_service)):
            ...
    """
    return StorageService()


# =============================================================================
# EJEMPLO DE USO
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Crear servicio (necesita credenciales en env vars)
    storage = StorageService()
    
    # Health check
    status = storage.health_check()
    print(f"Storage status: {status}")
    
    if status["status"] == "healthy":
        # Ejemplo: subir un thumbnail
        test_data = b"PNG test content..."
        result = storage.upload_thumbnail(
            fire_event_id="test-uuid-123",
            image_bytes=test_data,
            vis_type="RGB"
        )
        print(f"Upload result: {result}")
        
        # Obtener stats
        stats = storage.get_storage_stats()
        print(f"Storage stats: {stats}")
