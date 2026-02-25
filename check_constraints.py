from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    constraints = db.execute(text(" SELECT conname FROM pg_constraint WHERE conrelid =  AND contype = u \)).fetchall()
 print('UNIQUE constraints on vegetation_monitoring:', [c[0] for c in constraints])
 
 constraints = db.execute(text(\SELECT conname FROM pg_constraint WHERE conrelid =  AND contype = u \)).fetchall()
 print('UNIQUE constraints on land_use_changes:', [c[0] for c in constraints])
finally:
 db.close()
