import os
import sys

# Add project root to Python path
sys.path.append(os.getcwd())

from sqlalchemy import text
from app.api.deps import get_db
from app.db.session import SessionLocal

def run_migration():
    """Run the users table migration using SQLAlchemy."""
    print("Running migration for users table...")
    
    # Read the SQL file
    migration_file = os.path.join("migrations", "create_users.sql")
    if not os.path.exists(migration_file):
        print(f"Error: Migration file not found at {migration_file}")
        sys.exit(1)
        
    with open(migration_file, "r", encoding="utf-8") as f:
        sql_content = f.read()
        
    # Execute the SQL
    db = SessionLocal()
    try:
        # Split by statements to Execute them one by one if needed, 
        # but sqlalchemy.text usually handles blocks well.
        # However, for function definitions with $$ delimiters, it's safer to execute as a single block
        # or carefully split.
        # Let's try executing the whole block first.
        
        db.execute(text(sql_content))
        db.commit()
        print("Migration completed successfully!")
        
    except Exception as e:
        print(f"Error executing migration: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()
