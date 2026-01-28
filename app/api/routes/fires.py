from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import date

# Ajusta los imports según tu estructura
from app.api import deps       
from app.models.fire import FireEvent
from app.schemas.fire import FireEventRead

router = APIRouter()

@router.get("/", response_model=List[FireEventRead])
def read_fires(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
    min_date: Optional[date] = None,
    max_date: Optional[date] = None,
    significant_only: bool = False,
    province: Optional[str] = None
):
    """
    Lists fire events (clustered wildfires) with optional filtering by date range, significance, and province. Supports pagination via skip and limit

    ---
    Enumera eventos de incendios (incendios forestales agrupados) con filtrado opcional por rango de fechas, importancia y provincia. Admite paginación a través de skip y limit.


    """
    query = db.query(FireEvent)

    # Filtros
    if min_date:
        query = query.filter(FireEvent.start_date >= min_date)
    
    if max_date:
        query = query.filter(FireEvent.end_date <= max_date)

    if significant_only:
        query = query.filter(FireEvent.is_significant == True)
        
    if province:
        query = query.filter(FireEvent.province == province)

    # Ordenar por los más recientes
    fires = query.order_by(FireEvent.start_date.desc()).offset(skip).limit(limit).all()
    
    return fires

@router.get("/stats", tags=["stats"])
def read_fire_stats(db: Session = Depends(deps.get_db)):
    """
    Estadísticas simples (Sin caché por ahora para probar en local)
    """
    total = db.query(FireEvent).count()
    significant = db.query(FireEvent).filter(FireEvent.is_significant == True).count()
    
    # Agrupación por año
    years = db.query(
        func.extract('year', FireEvent.start_date).label('year'),
        func.count(FireEvent.id)
    ).group_by('year').order_by('year').all()

    return {
        "total_events": total,
        "significant_events": significant,
        "by_year": {int(year): count for year, count in years}
    }

@router.get("/{fire_id}", response_model=FireEventRead)
def read_fire_detail(
    fire_id: str,
    db: Session = Depends(deps.get_db)
):
    fire = db.query(FireEvent).filter(FireEvent.id == fire_id).first()
    if not fire:
        raise HTTPException(status_code=404, detail="Incendio no encontrado")
    return fire