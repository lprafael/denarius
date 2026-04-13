from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Emisor, Usuario
from app.schemas import EmisorOut, EmisorUpdate
from app.security import get_current_user, get_admin_user

router = APIRouter(prefix="/api/emisor", tags=["emisor"])


def _get_or_create_emisor(db: Session, empresa_id: int) -> Emisor:
    em = db.query(Emisor).filter(Emisor.empresa_id == empresa_id).first()
    if not em:
        # Generar un RUC temporal único basado en el ID para evitar el UniqueViolation
        temp_ruc = f"99999{empresa_id:03d}-0"
        
        # Si no existe, creamos uno con datos mínimos obligatorios para PostgreSQL
        em = Emisor(
            empresa_id=empresa_id, 
            ruc_con_dv=temp_ruc, 
            razon_social=f"EMPRESA CONFIGURANDO (ID {empresa_id})", 
            direccion="DIRECCION PENDIENTE"
        )
        db.add(em)
        db.commit()
        db.refresh(em)
    return em


@router.get("", response_model=EmisorOut)
def obtener(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    return _get_or_create_emisor(db, usuario.empresa_id)


@router.put("", response_model=EmisorOut)
def actualizar(
    body: EmisorUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_admin_user),
):
    em = _get_or_create_emisor(db, usuario.empresa_id)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(em, field, value)
    db.commit()
    db.refresh(em)
    return em
