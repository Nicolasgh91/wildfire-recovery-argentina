"""
Storage Service para ForestGuard.

Este módulo proporciona acceso a almacenamiento de objetos para:
- Thumbnails de imágenes satelitales
- PDFs de reportes y certificados
- Imágenes HD para descarga
"""

import hashlib
import logging
import mimetypes
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Union

import boto3

try:
    from google.cloud import storage as gcs_storage
except Exception:  # pragma: no cover - optional dependency
    gcs_storage = None

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURACIÓN
# =============================================================================

# Buckets predefinidos
BUCKETS = {
    "images": os.environ.get("STORAGE_BUCKET_IMAGES", "forestguard-images"),
    "reports": os.environ.get("STORAGE_BUCKET_REPORTS", "forestguard-reports"),
    "certificates": os.environ.get(
        "STORAGE_BUCKET_CERTIFICATES", "forestguard-certificates"
    ),
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
    Servicio de almacenamiento con backend configurable.

    Backends soportados:
    - "gcs": Google Cloud Storage
    - "r2": S3-compatible (legacy)
    - "local": filesystem local (Oracle VM)
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
        default_bucket: str = BUCKETS["images"],
    ):
        """
        Inicializa el servicio de storage.

        Args:
            access_key: Access Key ID (S3-compatible)
            secret_key: Secret Access Key (S3-compatible)
            endpoint_url: Endpoint URL (S3-compatible)
            default_bucket: Bucket por defecto
        """
        if self._initialized:
            return

        self._backend = os.environ.get("STORAGE_BACKEND", "gcs").lower()
        self._access_key = access_key
        self._secret_key = secret_key
        self._endpoint_url = endpoint_url
        self._default_bucket = default_bucket
        self._client = None
        self._gcs_project_id = os.environ.get("GCS_PROJECT_ID")
        self._gcs_credentials_path = os.environ.get(
            "GCS_SERVICE_ACCOUNT_JSON"
        ) or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        self._local_root = Path(
            os.environ.get("STORAGE_LOCAL_PATH", "storage")
        ).resolve()
        self._public_url_base = os.environ.get("STORAGE_PUBLIC_URL", "")
        self._initialized = True

    def _is_local(self) -> bool:
        return self._backend == "local"

    def _local_path(self, key: str, bucket: Optional[str]) -> Path:
        bucket = bucket or self._default_bucket
        return self._local_root / bucket / key

    def _get_client(self):
        """Obtiene o crea el cliente de storage."""
        if self._is_local():
            return None
        if self._backend == "gcs":
            if gcs_storage is None:
                raise StorageError(
                    "Falta dependencia google-cloud-storage. Instalar google-cloud-storage."
                )
            if self._client is None:
                if self._gcs_credentials_path:
                    self._client = gcs_storage.Client.from_service_account_json(
                        self._gcs_credentials_path,
                        project=self._gcs_project_id,
                    )
                else:
                    self._client = gcs_storage.Client(project=self._gcs_project_id)
            return self._client
        if self._client is None:
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
                region_name="auto",  # R2 usa 'auto'
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
        metadata: Optional[Dict[str, str]] = None,
    ) -> UploadResult:
        """
        Sube bytes al storage.

        Args:
            data: Contenido a subir
            key: Key (path) en el bucket
            bucket: Bucket destino (default: forestguard-images)
            content_type: MIME type (se infiere si no se proporciona)
            metadata: Metadata adicional

        Returns:
            UploadResult con detalles de la operación
        """
        bucket = bucket or self._default_bucket

        if self._is_local():
            # Write to local filesystem
            path = self._local_path(key, bucket)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "wb") as f:
                f.write(data)

            content_hash = hashlib.sha256(data).hexdigest()
            url = self.get_public_url(key, bucket)
            logger.info(f"Uploaded {len(data)} bytes to local {path}")

            return UploadResult(
                success=True,
                key=key,
                url=url,
                size_bytes=len(data),
                content_hash=content_hash,
            )

        if self._backend == "gcs":
            client = self._get_client()
            bucket_ref = client.bucket(bucket)
            blob = bucket_ref.blob(key)
            if metadata:
                blob.metadata = metadata
            blob.upload_from_string(data, content_type=content_type)
            content_hash = hashlib.sha256(data).hexdigest()
            url = self.get_public_url(key, bucket)
            logger.info(f"Uploaded {len(data)} bytes to {bucket}/{key}")
            return UploadResult(
                success=True,
                key=key,
                url=url,
                size_bytes=len(data),
                content_hash=content_hash,
            )

        client = self._get_client()

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

            client.put_object(Bucket=bucket, Key=key, Body=data, **extra_args)

            # Generar URL pública (si el bucket es público) o presignada
            url = self.get_public_url(key, bucket)

            logger.info(f"Uploaded {len(data)} bytes to {bucket}/{key}")

            return UploadResult(
                success=True,
                key=key,
                url=url,
                size_bytes=len(data),
                content_hash=content_hash,
            )

        except Exception as e:
            logger.error(f"Error uploading to {bucket}/{key}: {e}")
            return UploadResult(
                success=False,
                key=key,
                url="",
                size_bytes=0,
                content_hash="",
                error=str(e),
            )

    def upload_file(
        self,
        file_path: Union[str, Path],
        key: Optional[str] = None,
        bucket: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> UploadResult:
        """
        Sube un archivo local al storage.

        Args:
            file_path: Ruta al archivo local
            key: Key en storage (default: nombre del archivo)
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
            metadata=metadata,
        )

    def upload_thumbnail(
        self,
        fire_event_id: str,
        image_bytes: bytes,
        vis_type: str = "RGB",
        acquisition_date: Optional[Any] = None,
        format: str = "png",
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
            if hasattr(acquisition_date, "strftime"):
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
            metadata=metadata,
        )

    def upload_temporal_series(
        self, fire_event_id: str, images: Dict[str, bytes], vis_type: str = "RGB"
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
                    "series": "true",
                },
            )
            results[date_str] = result

        return results

    def upload_report_pdf(
        self, report_id: str, pdf_bytes: bytes, report_type: str = "historical"
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
                "generated_at": timestamp,
            },
        )

    # =========================================================================
    # MÉTODOS DE DESCARGA Y URLS
    # =========================================================================

    def get_signed_url(
        self,
        key: str,
        bucket: Optional[str] = None,
        expiry_seconds: int = DEFAULT_URL_EXPIRY,
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
        if self._is_local():
            return self.get_public_url(key, bucket)

        if self._backend == "gcs":
            client = self._get_client()
            bucket = bucket or self._default_bucket
            blob = client.bucket(bucket).blob(key)
            return blob.generate_signed_url(
                version="v4",
                expiration=timedelta(seconds=expiry_seconds),
                method="GET",
            )

        client = self._get_client()
        bucket = bucket or self._default_bucket

        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expiry_seconds,
        )

        return url

    def get_public_url(self, key: str, bucket: Optional[str] = None) -> str:
        """
        Genera URL pública (asume bucket con acceso público).

        Para backend con custom domain configurado.

        Args:
            key: Key del objeto
            bucket: Bucket

        Returns:
            URL pública
        """
        bucket = bucket or self._default_bucket
        if self._is_local():
            if self._public_url_base:
                return f"{self._public_url_base.rstrip('/')}/{bucket}/{key}"
            return str(self._local_path(key, bucket))

        if self._backend == "gcs":
            if self._public_url_base:
                return f"{self._public_url_base.rstrip('/')}/{bucket}/{key}"
            return f"https://storage.googleapis.com/{bucket}/{key}"

        public_url_base = os.environ.get("R2_PUBLIC_URL", "")
        if public_url_base:
            return f"{public_url_base.rstrip('/')}/{key}"
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
        bucket = bucket or self._default_bucket
        if self._is_local():
            path = self._local_path(key, bucket)
            if not path.exists():
                raise StorageNotFoundError(f"Objeto no encontrado: {bucket}/{key}")
            return path.read_bytes()

        if self._backend == "gcs":
            client = self._get_client()
            blob = client.bucket(bucket).blob(key)
            if not blob.exists():
                raise StorageNotFoundError(f"Objeto no encontrado: {bucket}/{key}")
            return blob.download_as_bytes()

        client = self._get_client()
        try:
            response = client.get_object(Bucket=bucket, Key=key)
            return response["Body"].read()
        except client.exceptions.NoSuchKey:
            raise StorageNotFoundError(f"Objeto no encontrado: {bucket}/{key}")

    def exists(self, key: str, bucket: Optional[str] = None) -> bool:
        """Verifica si un objeto existe."""
        bucket = bucket or self._default_bucket
        if self._is_local():
            return self._local_path(key, bucket).exists()

        if self._backend == "gcs":
            client = self._get_client()
            blob = client.bucket(bucket).blob(key)
            return blob.exists()

        client = self._get_client()
        try:
            client.head_object(Bucket=bucket, Key=key)
            return True
        except Exception:
            return False

    # =========================================================================
    # MÉTODOS DE LISTADO Y ESTADÍSTICAS
    # =========================================================================

    def list_objects(
        self, prefix: str = "", bucket: Optional[str] = None, max_keys: int = 1000
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
        bucket = bucket or self._default_bucket
        if self._is_local():
            base = self._local_root / bucket
            if not base.exists():
                return []
            objects = []
            for path in base.rglob("*"):
                if path.is_file():
                    rel = path.relative_to(base).as_posix()
                    if prefix and not rel.startswith(prefix):
                        continue
                    stat = path.stat()
                    objects.append(
                        {
                            "key": rel,
                            "size": stat.st_size,
                            "last_modified": datetime.fromtimestamp(stat.st_mtime),
                        }
                    )
                    if len(objects) >= max_keys:
                        break
            return objects

        if self._backend == "gcs":
            client = self._get_client()
            objects = []
            for blob in client.list_blobs(bucket, prefix=prefix, max_results=max_keys):
                objects.append(
                    {
                        "key": blob.name,
                        "size": blob.size,
                        "last_modified": blob.updated,
                    }
                )
            return objects

        client = self._get_client()
        response = client.list_objects_v2(
            Bucket=bucket, Prefix=prefix, MaxKeys=max_keys
        )

        objects = []
        for obj in response.get("Contents", []):
            objects.append(
                {
                    "key": obj["Key"],
                    "size": obj["Size"],
                    "last_modified": obj["LastModified"],
                }
            )

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
            prefix=f"{PREFIXES['thumbnails']}{fire_event_id}/", bucket=BUCKETS["images"]
        )

        series = self.list_objects(
            prefix=f"{PREFIXES['temporal_series']}{fire_event_id}/",
            bucket=BUCKETS["images"],
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
            by_prefix=by_prefix,
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
        bucket = bucket or self._default_bucket
        if self._is_local():
            path = self._local_path(key, bucket)
            try:
                if path.exists():
                    path.unlink()
                logger.info(f"Deleted local {bucket}/{key}")
                return True
            except Exception as e:
                logger.error(f"Error deleting local {bucket}/{key}: {e}")
                return False

        if self._backend == "gcs":
            try:
                client = self._get_client()
                blob = client.bucket(bucket).blob(key)
                blob.delete()
                logger.info(f"Deleted {bucket}/{key}")
                return True
            except Exception as e:
                logger.error(f"Error deleting {bucket}/{key}: {e}")
                return False

        client = self._get_client()
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
        dry_run: bool = True,
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
        Verifica el estado de la conexión con storage.

        Returns:
            Dict con status y detalles
        """
        try:
            if self._is_local():
                self._local_root.mkdir(parents=True, exist_ok=True)
                objects = self.list_objects(max_keys=10)
                return {
                    "status": "healthy",
                    "backend": "local",
                    "root": str(self._local_root),
                    "accessible": True,
                    "sample_objects": len(objects),
                }

            if self._backend == "gcs":
                client = self._get_client()
                bucket = client.bucket(self._default_bucket)
                if not bucket.exists():
                    raise StorageError(f"Bucket no existe: {self._default_bucket}")
                objects = self.list_objects(max_keys=10)
                return {
                    "status": "healthy",
                    "backend": "gcs",
                    "bucket": self._default_bucket,
                    "accessible": True,
                    "sample_objects": len(objects),
                }

            client = self._get_client()
            client.head_bucket(Bucket=self._default_bucket)
            objects = self.list_objects(max_keys=10)
            return {
                "status": "healthy",
                "backend": "r2",
                "bucket": self._default_bucket,
                "accessible": True,
                "sample_objects": len(objects),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "backend": self._backend,
                "accessible": False,
                "error": str(e),
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
            fire_event_id="test-uuid-123", image_bytes=test_data, vis_type="RGB"
        )
        print(f"Upload result: {result}")

        # Obtener stats
        stats = storage.get_storage_stats()
        print(f"Storage stats: {stats}")
