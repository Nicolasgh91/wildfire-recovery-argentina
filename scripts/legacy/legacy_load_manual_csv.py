"""
[DEPRECATED] - Codigo Legacy o Manual. Usar el flujo de Celery en su lugar.
"""
#!/usr/bin/env python3
import sys
import csv
from pathlib import Path

base_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(base_dir))

from scripts.maintenance.load_firms_incremental import (
    get_engine, get_fire_detection_columns, resolve_h3_resolution,
    filter_and_transform, insert_detections, run_clustering_for_dates, 
    run_area_calculation, run_legal_crossing
)

def process_csv(csv_path: str):
    csv_file = Path(csv_path)
    if not csv_file.exists():
        print(f"❌ Error: No se encontró el archivo {csv_file}")
        sys.exit(1)

    print(f"Leyendo {csv_file}...")
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        detections = list(reader)
        
    engine = get_engine()
    columns = get_fire_detection_columns(engine)
    supports_h3 = "h3_index" in columns
    supports_detection_hash = "detection_hash" in columns
    supports_created_at = "created_at" in columns
    h3_resolution = resolve_h3_resolution(engine)
    
    # Mapear detecciones según el satélite
    by_sat = {}
    for d in detections:
        # Acomodar campos de MODIS para que parezcan VIIRS
        if "brightness" in d:
            d["bright_ti4"] = d["brightness"]
        if "bright_t31" in d:
            d["bright_ti5"] = d["bright_t31"]
            
        inst = d.get("instrument", "VIIRS").upper()
        sat = d.get("satellite", "SNPP").upper()
        sat_key = f"{inst}_{sat}_NRT" 
        
        if sat_key not in by_sat:
            by_sat[sat_key] = []
        by_sat[sat_key].append(d)
        
    inserted_total = 0
    unique_dates = set()
    
    for sat_key, group in by_sat.items():
        print(f"Procesando {len(group)} registros de {sat_key}...")
        filtered = filter_and_transform(
            group,
            sat_key,
            compute_h3=supports_h3,
            h3_resolution=h3_resolution
        )
        for f in filtered:
            unique_dates.add(f['acquisition_date'])
        
        print(f"  Filtrados (alta confianza/dentro de Argentina): {len(filtered)}")
        
        if filtered:
            print(f"  Insertando {len(filtered)} registros (esto puede demorar unos minutos por la red...)")
            res = insert_detections(
                engine,
                filtered,
                supports_detection_hash=supports_detection_hash,
                supports_h3=supports_h3,
                supports_created_at=supports_created_at
            )
            print(f"  Insertados: {res['inserted']} (Duplicados ignorados: {res['duplicates']})")
            inserted_total += res['inserted']
        
    print(f"\n=========================================")
    print(f"Total insertados en DB: {inserted_total}")
    print(f"=========================================\n")
    
    if inserted_total > 0:
        print("Corriendo clustering...")
        events = run_clustering_for_dates(engine, list(unique_dates))
        print("Calculando áreas...")
        run_area_calculation(engine)
        print("Buscando cruces con áreas protegidas...")
        run_legal_crossing(engine)
        print("✅ Pipeline completado.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", help="Ruta al archivo CSV de FIRMS")
    args = parser.parse_args()
    process_csv(args.csv_path)

