"""
ForestGuard - Endpoints de Certificados (UC-07)

Endpoints:
- POST /issue - Emitir certificado de quema
- GET /download/{certificate_number} - Descargar PDF
- GET /verify/{certificate_number} - Verificar autenticidad
"""

import os
import json
import hashlib
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, text  # ← FIX: Agregar import de text
from pydantic import BaseModel

from app.api.deps import get_db
from app.models.fire import FireEvent
from app.models.certificate import BurnCertificate
from app.services.pdf_service import generate_certificate_pdf

router = APIRouter()


# Schema para la petición
class CertificateRequest(BaseModel):
    fire_event_id: str
    issued_to: str
    requester_email: str


@router.post("/issue")
async def issue_certificate(
    request: CertificateRequest,
    req: Request,
    db: Session = Depends(get_db)
):
    """
    Emite un certificado de quema.
    SOLO guarda el registro en BD. El PDF se genera al descargar.
    """
    # 1. Validar el evento
    event = db.query(FireEvent).filter(FireEvent.id == request.fire_event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="El incendio especificado no existe.")

    # 2. Generar Secuencia
    current_year = datetime.now().year
    count = db.query(BurnCertificate).filter(
        func.extract('year', BurnCertificate.issued_at) == current_year
    ).count()
    
    cert_number = f"CERT-{current_year}-{count + 1:06d}"

    # 3. Crear Snapshot de los datos y hash
    event_snapshot = {
        "fire_event_id": request.fire_event_id,
        "issued_to": request.issued_to,
        "requester_email": request.requester_email,
        "certificate_number": cert_number,
        "issued_at": datetime.now().isoformat(),
    }

    # Generar hash determinista del snapshot
    snapshot_json = json.dumps(event_snapshot, sort_keys=True, default=str)
    data_hash = hashlib.sha256(snapshot_json.encode()).hexdigest()

    new_cert = BurnCertificate(
        certificate_number=cert_number,
        fire_event_id=request.fire_event_id,
        issued_to=request.issued_to,
        requester_email=request.requester_email,
        data_hash=data_hash,
        snapshot_data=snapshot_json,
        issued_at=datetime.now()
    )

    db.add(new_cert)
    db.commit()
    db.refresh(new_cert)

    # 4. Construir URL de descarga dinámica
    base_url = str(req.base_url).rstrip("/")
    download_url = f"{base_url}/api/v1/certificates/download/{cert_number}"

    return {
        "status": "success",
        "certificate_number": cert_number,
        "issued_to": new_cert.issued_to,
        "download_url": download_url,
        "verification_hash": new_cert.data_hash
    }


@router.get("/download/{certificate_number}")
def download_pdf(
    certificate_number: str, 
    req: Request, 
    db: Session = Depends(get_db)
):
    """
    Genera el PDF en memoria (con QR) y lo devuelve para descarga directa.
    """
    # 1. Recuperar Certificado
    cert = db.query(BurnCertificate).filter(
        BurnCertificate.certificate_number == certificate_number
    ).first()
    
    if not cert:
        raise HTTPException(status_code=404, detail="Certificado no encontrado.")
    
    # 2. Recuperar Datos del Incendio
    event = db.query(FireEvent).filter(FireEvent.id == cert.fire_event_id).first()
    
    if not event:
        raise HTTPException(status_code=404, detail="Evento de incendio no encontrado.")
    
    # Extraer lat/lon del centroid (Geography)
    lat = 0.0
    lon = 0.0
    try:
        row = db.execute(
            text("SELECT ST_Y(centroid::geometry) AS lat, ST_X(centroid::geometry) AS lon FROM fire_events WHERE id = :id"),
            {"id": str(event.id)}
        ).first()
        if row is not None:
            lat = float(row.lat) if row.lat is not None else 0.0
            lon = float(row.lon) if row.lon is not None else 0.0
    except Exception:
        lat = 0.0
        lon = 0.0

    event_data = {
        "date": str(event.start_date.date()) if event.start_date else "N/A",
        "province": getattr(event, "province", None) or "N/A",
        "lat": lat,
        "lon": lon,
        "hectares": float(event.estimated_area_hectares) if event.estimated_area_hectares else 0.0,
        "frp": float(event.avg_frp) if event.avg_frp else 0.0
    }

    # 3. Construir URL de Verificación para el QR
    public_base = os.getenv("PUBLIC_BASE_URL")
    if public_base:
        base_url = public_base.rstrip("/")
    else:
        base_url = str(req.base_url).rstrip("/")
    verification_url = f"{base_url}/api/v1/certificates/verify/{certificate_number}"

    # 4. Generar PDF
    try:
        pdf_bytes = generate_certificate_pdf(cert, event_data, verification_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando el documento PDF: {str(e)}")

    # 5. Devolver como archivo adjunto
    filename = f"ForestGuard_{certificate_number}.pdf"
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/verify/{certificate_number}")
def verify_certificate(certificate_number: str, db: Session = Depends(get_db)):
    """
    Endpoint público que abre el celular al escanear el QR.
    Valida si el certificado es real.
    """
    cert = db.query(BurnCertificate).filter(
        BurnCertificate.certificate_number == certificate_number
    ).first()
    
    if not cert:
        return {
            "status": "INVALID",
            "message": "❌ Este certificado NO existe en los registros oficiales de ForestGuard."
        }
    
    return {
        "status": "VALID",
        "message": "✅ Certificado Oficial Verificado.",
        "data": {
            "number": cert.certificate_number,
            "issued_to": cert.issued_to,
            "date": cert.issued_at.isoformat() if cert.issued_at else None,
            "hash": cert.data_hash
        }
    }