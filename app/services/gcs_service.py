"""
Google Cloud Storage Service para ForestGuard
Maneja subida y descarga de imágenes satelitales usando Application Default Credentials

La razón por la que usamos ADC en lugar de Service Account JSON es la seguridad.
Con Service Account JSON, tienes una clave privada que puede ser expuesta en logs,
variables de entorno, o backups accidentales. Con ADC, Google Cloud detecta
automáticamente dónde estás corriendo (local, Docker, Cloud Run) y busca
credenciales válidas en el orden correcto sin que el desarrollador maneje claves.

En desarrollo: Lee de ~/.config/gcloud/application_default_credentials.json
En Docker: Lee del volumen montado que apunta a tu ~/.config/gcloud/
En Cloud Run: Automático via metadata service, sin configuración manual

Esta arquitectura es mucho más segura y sigue las mejores prácticas de Google Cloud.
"""

import logging
import os
from datetime import timedelta
from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Optional

from google.auth.exceptions import DefaultCredentialsError
from google.cloud import storage

logger = logging.getLogger(__name__)


class GCSService:
    """
    Servicio para interactuar con Google Cloud Storage.

    Esta clase proporciona métodos simples para las operaciones más comunes:
    - Subir archivos
    - Descargar archivos
    - Generar URLs presignadas (acceso temporal sin credenciales GCS)
    - Borrar archivos

    El patrón de diseño aquí es Singleton: se crea una sola instancia del servicio
    que se reutiliza en toda la aplicación. Esto es importante porque el cliente
    de GCS mantiene una conexión que puede ser costosa de recrear.
    """

    _instance = None  # Para patrón Singleton

    def __new__(cls, *args, **kwargs):
        """
        Patrón Singleton: asegura que solo existe una instancia del servicio.
        Cuando alguien llama a GCSService(), siempre obtiene la misma instancia.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, project_id: Optional[str] = None):
        """
        Inicializa el servicio GCS.

        Args:
            project_id: ID del proyecto GCP. Si no se proporciona, se intenta
                       obtener del ambiente. En Cloud Run, se detecta automáticamente.

        Raises:
            DefaultCredentialsError: Si no se pueden encontrar credenciales válidas.
            ValueError: Si no se puede determinar el project_id.
        """
        # Solo inicializar una vez (patrón Singleton)
        if self._initialized:
            return

        # Obtener project ID
        if not project_id:
            project_id = os.getenv("GCS_PROJECT_ID")

        if not project_id:
            raise ValueError(
                "GCS_PROJECT_ID no está configurado. "
                "Agrega a .env: GCS_PROJECT_ID=tu-gcp-project-id"
            )

        self.project_id = project_id

        # Crear cliente de GCS
        # IMPORTANTE: No pasamos credenciales explícitamente.
        # El cliente de Google Cloud busca automáticamente en:
        # 1. Variable de entorno GOOGLE_APPLICATION_CREDENTIALS (archivo JSON)
        # 2. ~/.config/gcloud/application_default_credentials.json (local)
        # 3. Metadata service (Cloud Run, Compute Engine, Kubernetes)
        # 4. Credenciales del usuario logueado en gcloud CLI
        try:
            self.client = storage.Client(project=project_id)
            logger.info(f"✅ GCS client inicializado para proyecto: {project_id}")
        except DefaultCredentialsError as e:
            logger.error(
                "❌ No se encontraron credenciales de GCP válidas. "
                "En desarrollo, ejecuta: gcloud auth application-default login"
            )
            raise

        self._initialized = True

    def upload_image(
        self,
        local_file_path: str,
        bucket_name: str,
        destination_blob_name: str,
        content_type: str = "image/tiff",
    ) -> Optional[str]:
        """
        Sube un archivo local a Google Cloud Storage.

        Args:
            local_file_path: Ruta del archivo en tu máquina/contenedor
            bucket_name: Nombre del bucket GCS (ej: "forestguard-images")
            destination_blob_name: Ruta dentro del bucket (ej: "hd/incendio_123.tif")
            content_type: MIME type del archivo (ej: "image/tiff", "image/jpeg")

        Returns:
            URL pública del archivo, o None si hay error

        Ejemplo de uso en un worker Celery:

            @celery_app.task
            def download_and_upload_satellite_image(fire_id):
                # Descargar imagen desde API
                image_data = download_from_nasa_api(fire_id)

                # Guardar localmente temporalmente
                temp_path = f"/tmp/{fire_id}.tif"
                with open(temp_path, 'wb') as f:
                    f.write(image_data)

                # Subir a GCS
                gcs = GCSService()
                public_url = gcs.upload_image(
                    local_file_path=temp_path,
                    bucket_name="forestguard-images",
                    destination_blob_name=f"hd/{fire_id}.tif",
                    content_type="image/tiff"
                )

                # Guardar URL en BD para acceso posterior
                db.execute(
                    "UPDATE fire_detections SET image_url = %s WHERE id = %s",
                    (public_url, fire_id)
                )

                # Limpiar archivo temporal
                os.remove(temp_path)

                return public_url
        """
        try:
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(destination_blob_name)

            # Configurar tipo de contenido (permite al navegador mostrar imagen directamente)
            blob.content_type = content_type

            # Subir el archivo
            logger.info(f"⬆️  Subiendo {destination_blob_name} a {bucket_name}...")
            blob.upload_from_filename(local_file_path)

            # Hacer la imagen pública para acceso sin credenciales
            # En producción, podrías usar URLs presignadas en lugar de esto
            # (más seguro, expira automáticamente después de tiempo)
            blob.make_public()

            public_url = blob.public_url
            logger.info(f"✅ Archivo subido: {public_url}")

            return public_url

        except Exception as e:
            logger.error(f"❌ Error subiendo a GCS: {e}")
            return None

    def upload_from_bytes(
        self,
        file_bytes: bytes,
        bucket_name: str,
        destination_blob_name: str,
        content_type: str = "image/tiff",
    ) -> Optional[str]:
        """
        Sube un archivo desde bytes (útil para datos en memoria).

        Args:
            file_bytes: Contenido del archivo en bytes
            bucket_name: Nombre del bucket GCS
            destination_blob_name: Ruta dentro del bucket
            content_type: MIME type

        Returns:
            URL pública del archivo

        Ejemplo en un worker:

            @celery_app.task
            def process_fire_image(fire_id, image_bytes):
                gcs = GCSService()
                url = gcs.upload_from_bytes(
                    file_bytes=image_bytes,
                    bucket_name="forestguard-images",
                    destination_blob_name=f"hd/{fire_id}.tif"
                )
                return url
        """
        try:
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(destination_blob_name)
            blob.content_type = content_type

            logger.info(
                f"⬆️  Subiendo {destination_blob_name} ({len(file_bytes)} bytes)..."
            )
            blob.upload_from_string(file_bytes)
            blob.make_public()

            public_url = blob.public_url
            logger.info(f"✅ Archivo subido: {public_url}")

            return public_url

        except Exception as e:
            logger.error(f"❌ Error subiendo a GCS: {e}")
            return None

    def download_image(self, bucket_name: str, blob_name: str) -> Optional[bytes]:
        """
        Descarga un archivo de GCS como bytes.

        Args:
            bucket_name: Nombre del bucket
            blob_name: Ruta del archivo dentro del bucket

        Returns:
            Contenido del archivo en bytes, o None si error

        Útil cuando necesitas procesar una imagen ya almacenada:

            gcs = GCSService()
            image_bytes = gcs.download_image(
                bucket_name="forestguard-images",
                blob_name="hd/incendio_123.tif"
            )
            # Procesar image_bytes...
        """
        try:
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(blob_name)

            logger.info(f"⬇️  Descargando {blob_name}...")
            data = blob.download_as_bytes()
            logger.info(f"✅ Descargado: {len(data)} bytes")

            return data

        except Exception as e:
            logger.error(f"❌ Error descargando de GCS: {e}")
            return None

    def get_signed_url(
        self, bucket_name: str, blob_name: str, expiration_hours: int = 24
    ) -> Optional[str]:
        """
        Genera una URL presignada (temporal) para acceso sin credenciales GCS.

        Una URL presignada es más segura que hacer un blob público porque:
        - Solo funciona durante el período especificado (por defecto 24 horas)
        - Incluye firma criptográfica que valida la solicitud
        - No requiere que el usuario tenga credenciales de GCS

        Args:
            bucket_name: Nombre del bucket
            blob_name: Ruta del archivo
            expiration_hours: Cuántas horas será válida la URL (máximo 7 días)

        Returns:
            URL presignada que puede compartirse con usuarios

        Ejemplo en un endpoint FastAPI:

            @app.get("/reports/{fire_id}/download")
            def download_report(fire_id: str, db: Session = Depends(get_db)):
                # Obtener ubicación del reporte de BD
                report = db.query(DestructionReport).filter(
                    DestructionReport.fire_id == fire_id
                ).first()

                if not report:
                    raise HTTPException(404, "Reporte no encontrado")

                # Generar URL presignada para descargar
                gcs = GCSService()
                download_url = gcs.get_signed_url(
                    bucket_name="forestguard-reports",
                    blob_name=report.gcs_path,
                    expiration_hours=24
                )

                return {"download_url": download_url, "expires_in_hours": 24}
        """
        try:
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(blob_name)

            # Generar URL firmada que expira en N horas
            signed_url = blob.generate_signed_url(
                version="v4",  # Versión más nueva de Google Cloud Storage
                expiration=timedelta(hours=expiration_hours),  # Cuando expira
            )

            logger.info(
                f"🔗 URL presignada generada para {blob_name} (válida {expiration_hours}h)"
            )
            return signed_url

        except Exception as e:
            logger.error(f"❌ Error generando URL presignada: {e}")
            return None

    def delete_image(self, bucket_name: str, blob_name: str) -> bool:
        """
        Borra un archivo de GCS.

        Args:
            bucket_name: Nombre del bucket
            blob_name: Ruta del archivo a borrar

        Returns:
            True si se borró exitosamente, False si hay error

        Útil para limpiar archivos temporales o cuando se borra un evento:

            gcs = GCSService()
            if gcs.delete_image("forestguard-images", "hd/temp_file.tif"):
                logger.info("Archivo borrado")
            else:
                logger.error("Fallo al borrar")
        """
        try:
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(blob_name)

            logger.info(f"🗑️  Borrando {blob_name}...")
            blob.delete()
            logger.info(f"✅ Archivo borrado")

            return True

        except Exception as e:
            logger.error(f"❌ Error borrando de GCS: {e}")
            return False

    def list_blobs(self, bucket_name: str, prefix: str = "") -> list:
        """
        Lista todos los archivos en un bucket (opcionalmente filtrado por prefijo).

        Args:
            bucket_name: Nombre del bucket
            prefix: Filtrar por prefijo (ej: "hd/" para solo archivos HD)

        Returns:
            Lista de nombres de blobs (archivos)

        Útil para auditoría o limpieza:

            gcs = GCSService()
            all_hd_images = gcs.list_blobs(
                bucket_name="forestguard-images",
                prefix="hd/"
            )
            print(f"Total imágenes HD: {len(all_hd_images)}")
        """
        try:
            bucket = self.client.bucket(bucket_name)
            blobs = bucket.list_blobs(prefix=prefix)

            # Retornar nombres de los blobs
            return [blob.name for blob in blobs]

        except Exception as e:
            logger.error(f"❌ Error listando blobs: {e}")
            return []


# Singleton global para usar en toda la aplicación
# En lugar de crear new GCSService() cada vez, importas esto:
#   from gcs_service import gcs_service
#   gcs_service.upload_image(...)
gcs_service = GCSService()
