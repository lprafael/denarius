from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuditLog, Usuario
from app.schemas import AuditLogOut
from app.security import get_admin_user

router = APIRouter(prefix="/api/auditoria", tags=["auditoria"])


@router.get("", response_model=list[AuditLogOut])
def listar(
    skip: int = 0,
    limit: int = 100,
    accion: str | None = None,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_admin_user),
):
    """Devuelve los registros de auditoría de la empresa. Solo admin."""
    q = db.query(AuditLog).filter(AuditLog.empresa_id == usuario.empresa_id)
    if accion:
        q = q.filter(AuditLog.accion == accion)
    return q.order_by(AuditLog.id.desc()).offset(skip).limit(limit).all()
