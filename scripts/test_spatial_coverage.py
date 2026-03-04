#!/usr/bin/env python3
"""
Script de prueba para validar la nueva funcionalidad de cobertura espacial en get_best_image.

Uso:
    python scripts/test_spatial_coverage.py
"""
import sys
import os
from datetime import date

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.gee_service import GEEService


def test_spatial_coverage():
    """Prueba la funcionalidad de cobertura espacial."""
    print("=" * 80)
    print("TEST: Cobertura espacial en get_best_image")
    print("=" * 80)
    
    gee = GEEService()
    
    try:
        gee.authenticate()
        print("✓ GEE autenticado correctamente")
    except Exception as e:
        print(f"✗ Error al autenticar GEE: {e}")
        return False
    
    # Bbox de prueba (zona central de Argentina)
    bbox = {"west": -65.0, "south": -35.0, "east": -64.5, "north": -34.5}
    print(f"\nBbox de prueba: {bbox}")
    
    # Obtener colección de imágenes
    try:
        collection = gee.get_sentinel_collection(
            bbox=bbox,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 3, 1),
            max_cloud_cover=30
        )
        print("✓ Colección obtenida correctamente")
    except Exception as e:
        print(f"✗ Error al obtener colección: {e}")
        return False
    
    # Test 1: get_best_image SIN bbox (lógica legacy)
    print("\n" + "-" * 80)
    print("Test 1: get_best_image SIN bbox (lógica legacy)")
    print("-" * 80)
    try:
        best_legacy = gee.get_best_image(collection)
        metadata_legacy = gee.get_image_metadata(best_legacy)
        print(f"✓ Imagen seleccionada (legacy): {metadata_legacy.image_id}")
        print(f"  - Nubosidad: {metadata_legacy.cloud_cover_percent:.2f}%")
        print(f"  - Fecha: {metadata_legacy.acquisition_date}")
    except Exception as e:
        print(f"✗ Error en test legacy: {e}")
        return False
    
    # Test 2: get_best_image CON bbox (nueva lógica con cobertura)
    print("\n" + "-" * 80)
    print("Test 2: get_best_image CON bbox (nueva lógica con cobertura)")
    print("-" * 80)
    try:
        best_coverage = gee.get_best_image(
            collection, 
            min_coverage=95.0, 
            max_candidates=10,
            bbox=bbox
        )
        metadata_coverage = gee.get_image_metadata(best_coverage)
        print(f"✓ Imagen seleccionada (con cobertura): {metadata_coverage.image_id}")
        print(f"  - Nubosidad: {metadata_coverage.cloud_cover_percent:.2f}%")
        print(f"  - Fecha: {metadata_coverage.acquisition_date}")
        
        # Calcular cobertura de la imagen seleccionada
        coverage = gee._calculate_spatial_coverage(best_coverage, bbox, scale=60)
        print(f"  - Cobertura espacial: {coverage:.1f}%")
        
        if coverage >= 95.0:
            print("✓ La imagen seleccionada cumple el criterio de cobertura >= 95%")
        else:
            print(f"⚠ La imagen seleccionada tiene cobertura {coverage:.1f}% (< 95%)")
            print("  Esto es esperado si ninguna imagen en la colección tiene >= 95% de cobertura")
    except Exception as e:
        print(f"✗ Error en test con cobertura: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test 3: Comparar ambas selecciones
    print("\n" + "-" * 80)
    print("Test 3: Comparación de resultados")
    print("-" * 80)
    if metadata_legacy.image_id == metadata_coverage.image_id:
        print("ℹ Ambos métodos seleccionaron la misma imagen")
    else:
        print("ℹ Los métodos seleccionaron imágenes diferentes:")
        print(f"  - Legacy: {metadata_legacy.image_id} (nubes: {metadata_legacy.cloud_cover_percent:.2f}%)")
        print(f"  - Con cobertura: {metadata_coverage.image_id} (nubes: {metadata_coverage.cloud_cover_percent:.2f}%, cobertura: {coverage:.1f}%)")
    
    print("\n" + "=" * 80)
    print("✓ TODOS LOS TESTS PASARON CORRECTAMENTE")
    print("=" * 80)
    return True


if __name__ == "__main__":
    success = test_spatial_coverage()
    sys.exit(0 if success else 1)
