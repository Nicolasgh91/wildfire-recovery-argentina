import pandas as pd
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CSV_Splitter")

class CsvSplitter:
    def __init__(self, output_dir: str = "output"):
        self.base_dir = Path(__file__).resolve().parent
        self.output_dir = self.base_dir / output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def split_by_year(self, file_path: str, target_year: int = None, chunk_size: int = 50000):
        """
        Si target_year es None, guarda todos los años.
        Si target_year tiene valor (ej: 2023), solo guarda ese año.
        """
        logger.info(f"--- Procesando {file_path} (Filtro Año: {target_year}) ---")
        
        files_created = set()

        try:
            for i, chunk in enumerate(pd.read_csv(file_path, parse_dates=['acq_date'], chunksize=chunk_size)):
                chunk['year'] = chunk['acq_date'].dt.year
                
                # --- Lógica de Filtro ---
                if target_year is not None:
                    chunk = chunk[chunk['year'] == target_year]

                if chunk.empty:
                    continue

                for year, data in chunk.groupby('year'):
                    output_file = self.output_dir / f"fires_{year}.csv"
                    mode = 'a' if output_file.exists() else 'w'
                    header = False if output_file.exists() else True
                    
                    data.drop(columns=['year']).to_csv(output_file, mode=mode, header=header, index=False)
                    files_created.add(str(output_file.name))
                    
                logger.info(f"Bloque {i+1} procesado.")

            return {"status": "success", "files_generated": list(files_created)}

        except Exception as e:
            logger.error(f"Error: {e}")
            raise e