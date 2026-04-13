from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Certificado, EventoDE, Factura, EstadoEnvioDE, Usuario
from app.schemas import EventoCreate, EventoOut
from app.security import get_current_user, registrar_audit

router = APIRouter(prefix="/api/eventos", tags=["eventos"])

TIPOS_VALIDOS = {
    "cancel": "gEvCan",
    "conformidad": "gEvConf",
    "disconformidad": "gEvDisconf",
    "desconocimiento": "gEvDesc",
    "nominacion": "gEvNom",
}


@router.get("", response_model=list[EventoOut])
def listar(
    factura_id: int | None = None,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    q = db.query(EventoDE).filter(EventoDE.empresa_id == usuario.empresa_id)
    if factura_id:
        q = q.filter(EventoDE.factura_id == factura_id)
    return q.order_by(EventoDE.id.desc()).limit(200).all()


@router.post("", response_model=EventoOut, status_code=201)
def crear_evento(
    body: EventoCreate,
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """
    Envía un evento al SIFEN (cancelación, conformidad, etc.)
    El DE debe estar previamente aprobado por SIFEN.
    """
    if body.tipo_evento not in TIPOS_VALIDOS:
        raise HTTPException(400, f"tipo_evento inválido. Opciones: {list(TIPOS_VALIDOS.keys())}")

    factura = db.query(Factura).filter(
        Factura.id == body.factura_id,
        Factura.empresa_id == usuario.empresa_id,
    ).first()
    if not factura:
        raise HTTPException(404, "Factura no encontrada")

    tag_evento = TIPOS_VALIDOS[body.tipo_evento]

    from app.sifen.sifen_client import enviar_evento
    resultado = enviar_evento(
        tipo_evento=tag_evento,
        cdc=factura.cdc,
        motivo=body.motivo,
    )

    # Si es cancelación exitosa, marcar la factura
    if body.tipo_evento == "cancel" and resultado.get("aprobado"):
        factura.cancelado = True
        factura.cancelado_at = datetime.now(timezone.utc).replace(tzinfo=None)
        factura.motivo_cancelacion = body.motivo

    evento = EventoDE(
        factura_id=body.factura_id,
        empresa_id=usuario.empresa_id,
        tipo_evento=body.tipo_evento,
        motivo=body.motivo,
        estado="aprobado" if resultado.get("aprobado") else "rechazado",
        sifen_respuesta=resultado.get("raw", "")[:4000],
        enviado_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(evento)
    db.commit()
    db.refresh(evento)

    ip = request.client.host if request.client else ""
    registrar_audit(db, accion=f"evento_{body.tipo_evento}", empresa_id=usuario.empresa_id,
                    usuario_id=usuario.id, entidad="factura", entidad_id=str(body.factura_id),
                    detalle=f"motivo:{body.motivo}", ip=ip)
    return evento
