"""
Bbox validation and conversion utilities for UC-F12 optimization
"""

import logging
from typing import Dict, Union

logger = logging.getLogger(__name__)

def validate_and_convert_bbox(bbox: Dict[str, float]) -> Dict[str, float]:
    """
    Validate and convert bbox to GEE format.
    
    Args:
        bbox: Bbox in any format
        
    Returns:
        Bbox in GEE format (west, south, east, north)
    """
    logger.info(f"🔍 [BBOX] Validating bbox: {bbox}")
    logger.info(f"🔍 [BBOX] Bbox type: {type(bbox)}")
    logger.info(f"🔍 [BBOX] Bbox keys: {list(bbox.keys())}")
    
    # Check if already in GEE format
    if all(key in bbox for key in ['west', 'south', 'east', 'north']):
        logger.info("✅ [BBOX] Already in GEE format")
        
        # Validate coordinate values
        west = bbox['west']
        south = bbox['south']
        east = bbox['east']
        north = bbox['north']
        
        if not all(isinstance(v, (int, float)) for v in [west, south, east, north]):
            raise ValueError(f"Bbox coordinates must be numeric. Got: {bbox}")
        
        if west >= east or south >= north:
            raise ValueError(f"Invalid bbox coordinates. west must be < east and south must be < north. Got: {bbox}")
        
        logger.info(f"✅ [BBOX] Validated GEE bbox: {bbox}")
        return bbox
    
    # Convert from min/max format
    if all(key in bbox for key in ['min_lon', 'max_lon', 'min_lat', 'max_lat']):
        logger.info("🔄 [BBOX] Converting from min/max to GEE format")
        
        min_lon = bbox['min_lon']
        max_lon = bbox['max_lon']
        min_lat = bbox['min_lat']
        max_lat = bbox['max_lat']
        
        if not all(isinstance(v, (int, float)) for v in [min_lon, max_lon, min_lat, max_lat]):
            raise ValueError(f"Bbox coordinates must be numeric. Got: {bbox}")
        
        if min_lon >= max_lon or min_lat >= max_lat:
            raise ValueError(f"Invalid bbox coordinates. min_lon must be < max_lon and min_lat must be < max_lat. Got: {bbox}")
        
        converted = {
            'west': min_lon,
            'east': max_lon,
            'south': min_lat,
            'north': max_lat
        }
        logger.info(f"✅ [BBOX] Converted to GEE format: {converted}")
        return converted
    
    # Unknown format
    available_keys = list(bbox.keys())
    logger.error(f"❌ [BBOX] Unknown bbox format. Available keys: {available_keys}")
    
    raise ValueError(f"Invalid bbox format. Expected keys: west/south/east/north or min_lon/max_lon/min_lat/max_lat. Got: {available_keys}")

def create_bbox_from_coordinates(
    lat: float,
    lon: float,
    buffer_degrees: float = 0.01,
    aspect_ratio: float = 1.0,
) -> Dict[str, float]:
    """
    Create bbox in GEE format from center coordinates.

    Args:
        lat: Latitude coordinate
        lon: Longitude coordinate
        buffer_degrees: Buffer around center point in degrees (used as half-height)
        aspect_ratio: Width/height ratio. 1.0 = square, 1.333 = 4:3.

    Returns:
        Bbox in GEE format
    """
    half_height = buffer_degrees
    half_width = half_height * aspect_ratio

    logger.info(f"🔍 [BBOX] Creating bbox from lat={lat:.4f}, lon={lon:.4f}, buffer={buffer_degrees}, ar={aspect_ratio}")

    bbox = {
        'west': lon - half_width,
        'east': lon + half_width,
        'south': lat - half_height,
        'north': lat + half_height,
    }

    logger.info(f"✅ [BBOX] Created bbox: {bbox}")
    return bbox
