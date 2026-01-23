from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from splitter import CsvSplitter
import shutil
import os
from pathlib import Path
from typing import Optional

app = FastAPI(title="Data Ingestion Service")
splitter = CsvSplitter(output_dir="output")

@app.post("/ingest/split-dataset")
async def split_dataset(
    file: UploadFile = File(...), 
    year: Optional[int] = Query(None, description="Año específico para filtrar (ej: 2024). Si se omite, procesa todos.")
):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Formato debe ser .csv")

    temp_path = Path("temp_upload.csv")
    
    try:
        # 1. Guardar archivo temporalmente
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 2. Ejecutar splitter con el filtro de año
        result = splitter.split_by_year(str(temp_path), target_year=year)
        
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Bloque finally asegura que se borre siempre, incluso si hay error
        if temp_path.exists():
            os.remove(temp_path)

if __name__ == "__main__":
    import uvicorn
    # '0.0.0.0' permite conexiones externas, pero localmente usa 127.0.0.1
    uvicorn.run(app, host="0.0.0.0", port=8002)