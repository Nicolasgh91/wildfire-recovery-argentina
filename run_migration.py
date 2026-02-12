import os
import psycopg2
from dotenv import load_dotenv

# 1. Cargar explícitamente el archivo .env
load_dotenv()

# 2. Obtener las variables individuales
db_host = os.getenv("DB_HOST")
db_port = int(os.getenv("DB_PORT", 5432))
db_name = os.getenv("DB_NAME")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")

# Ruta al archivo SQL                                   database/migrations/016_add_hd_generation_job_idempotency.sql
migration_path = os.path.join(os.path.dirname(__file__), "database", "migrations", "016_add_hd_generation_job_idempotency.sql")

try:
    print(f"📡 Conectando a Supabase en: {db_host}:{db_port}...")
    
    # 3. Conectar usando los parámetros individuales
    # Supabase (puerto 6543) requiere sslmode='require' generalmente
    conn = psycopg2.connect(
        host=db_host,
        port=db_port,
        dbname=db_name,
        user=db_user,
        password=db_password,
        sslmode='require' 
    )
    cursor = conn.cursor()
    
    print(f"📖 Leyendo archivo de migración: {migration_path}")
    with open(migration_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()
        
    print("🚀 Ejecutando SQL...")
    cursor.execute(sql_content)
    conn.commit()
    print("✅ Migración aplicada con éxito.")

except FileNotFoundError:
    print(f"❌ Error: No se encontró el archivo '{migration_path}'")
except psycopg2.OperationalError as e:
    print(f"❌ Error de Conexión: Verificá tus credenciales en el .env.")
    print(f"Detalle: {e}")
except Exception as e:
    print(f"❌ Error inesperado: {e}")
finally:
    if 'conn' in locals() and conn: conn.close()