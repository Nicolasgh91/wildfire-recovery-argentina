import oci
import logging

logger = logging.getLogger(__name__)

class OCIStorageService:
    def __init__(self):
        try:
            self.config = oci.config.from_file()
            self.client = oci.object_storage.ObjectStorageClient(self.config)
            self.namespace = self.client.get_namespace().data
            self.compartment_id = self.config.get("tenancy")
            
            logger.info(f"✅ OCI Object Storage inicializado (namespace: {self.namespace})")
        except Exception as e:
            logger.error(f"❌ Error inicializando OCI: {e}")
            raise
    
    def upload_file(self, bucket_name: str, object_name: str, file_bytes: bytes) -> str:
        """Sube un archivo a Object Storage"""
        try:
            self.client.put_object(
                namespace_name=self.namespace,
                bucket_name=bucket_name,
                object_name=object_name,
                put_object_body=file_bytes
            )
            
            url = f"https://objectstorage.us-ashburn-1.oraclecloud.com/n/{self.namespace}/b/{bucket_name}/o/{object_name}"
            logger.info(f"✅ Archivo subido: {object_name}")
            return url
        except Exception as e:
            logger.error(f"❌ Error subiendo archivo: {e}")
            raise
    
    def download_file(self, bucket_name: str, object_name: str):
        """Descarga un archivo"""
        try:
            response = self.client.get_object(
                namespace_name=self.namespace,
                bucket_name=bucket_name,
                object_name=object_name
            )
            file_bytes = response.data.content
            logger.info(f"✅ Archivo descargado: {object_name}")
            return file_bytes
        except Exception as e:
            logger.error(f"❌ Error descargando archivo: {e}")
            return None
    
    def delete_file(self, bucket_name: str, object_name: str) -> bool:
        """Borra un archivo"""
        try:
            self.client.delete_object(
                namespace_name=self.namespace,
                bucket_name=bucket_name,
                object_name=object_name
            )
            logger.info(f"✅ Archivo borrado: {object_name}")
            return True
        except Exception as e:
            logger.error(f"❌ Error borrando archivo: {e}")
            return False
    
    def list_objects(self, bucket_name: str, prefix: str = "") -> list:
        """Lista archivos en un bucket"""
        try:
            response = self.client.list_objects(
                namespace_name=self.namespace,
                bucket_name=bucket_name,
                prefix=prefix
            )
            objects = [obj.name for obj in response.data.objects] if response.data.objects else []
            logger.info(f"✅ Listado: {len(objects)} objetos")
            return objects
        except Exception as e:
            logger.error(f"❌ Error listando objetos: {e}")
            return []

# Instancia global
oci_storage = OCIStorageService()
