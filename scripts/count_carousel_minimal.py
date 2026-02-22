import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

# Load .env
load_dotenv(PROJECT_ROOT / ".env")

def ensure_db_url():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        host = os.getenv("DB_HOST")
        user = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")
        port = os.getenv("DB_PORT", "5432")
        dbname = os.getenv("DB_NAME", "postgres")
        
        if host and user:
            from urllib.parse import quote_plus
            encoded_password = quote_plus(password) if password else ""
            db_url = f"postgresql://{user}:{encoded_password}@{host}:{port}/{dbname}"
            os.environ["DATABASE_URL"] = db_url

def main():
    ensure_db_url()
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not found.")
        return

    try:
        engine = create_engine(db_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal()
        
        query = text("SELECT id FROM fire_episodes WHERE jsonb_array_length(slides_data) > 0")
        result = db.execute(query).fetchall()
        
        print(f"Count: {len(result)}")
        for row in result:
             print(f"ID: {row[0]}")
             
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
