from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from app.database import get_db
from app.models import FacturaRecibida, Usuario, Producto
from app.schemas import FacturaRecibidaOut
from app.security import get_current_user

router = APIRouter(prefix="/api/compras", tags=["compras"])

@router.get("", response_model=List[FacturaRecibidaOut])
def listar_compras(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    return db.query(FacturaRecibida).filter(
        FacturaRecibida.empresa_id == usuario.empresa_id
    ).all()

@router.post("/sync")
def sincronizar_compras(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    """
    Simula la recuperación de facturas emitidas a favor del RUC de la empresa desde SIFEN.
    """
    # Placeholder: En producción esto usará un robot o API de consulta por RUC si disponible
    return {"ok": True, "message": "Sincronización completada. No se encontraron nuevos documentos."}

@router.post("/registrar", response_model=FacturaRecibidaOut)
def registrar_compra_manual(
    cdc: str,
    ruc_emisor: str,
    razon_social: str,
    total: int,
    iva: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    # Verificar si ya existe el CDC
    existente = db.query(FacturaRecibida).filter(
        FacturaRecibida.cdc == cdc
    ).first()
    if existente:
        raise HTTPException(400, "Esta factura ya ha sido registrada.")
        
    nueva = FacturaRecibida(
        empresa_id=usuario.empresa_id,
        cdc=cdc,
        emisor_ruc=ruc_emisor,
        emisor_razon_social=razon_social,
        fecha_emision=datetime.now(), # Simplificado
        monto_total=total,
        monto_iva=iva
    )
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva
