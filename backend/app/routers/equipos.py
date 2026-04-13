from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Usuario, EquipoAutorizado, Empresa
from app.schemas import EquipoAutorizadoOut, EquipoAutorizadoUpdate
from app.security import get_admin_user, get_current_user, registrar_audit

router = APIRouter(prefix="/api/equipos", tags=["equipos"])


@router.get("", response_model=list[EquipoAutorizadoOut])
def listar_equipos(
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_admin_user),
):
    """
    Lista todos los equipos de la empresa del admin (solicitudes y autorizados).
    """
    # Unir con Usuario para filtrar por empresa_id
    query = db.query(EquipoAutorizado).join(Usuario).filter(Usuario.empresa_id == admin.empresa_id)
    return query.all()


@router.put("/{equipo_id}", response_model=EquipoAutorizadoOut)
def actualizar_equipo(
    equipo_id: int,
    body: EquipoAutorizadoUpdate,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_admin_user),
):
    """
    Autoriza, desautoriza o renombra un equipo.
    """
    equipo = db.query(EquipoAutorizado).join(Usuario).filter(
        EquipoAutorizado.id == equipo_id,
        Usuario.empresa_id == admin.empresa_id
    ).first()
    
    if not equipo:
        raise HTTPException(404, "Equipo no encontrado")

    if body.autorizado is not None:
        # Verificar si la empresa tiene restricción y si llegamos al límite
        empresa = db.query(Empresa).filter(Empresa.id == admin.empresa_id).first()
        if body.autorizado and empresa.max_equipos > 0:
            # Contar equipos autorizados actualmente en la empresa
            total_autorizados = db.query(EquipoAutorizado).join(Usuario).filter(
                Usuario.empresa_id == admin.empresa_id,
                EquipoAutorizado.autorizado == True
            ).count()
            
            if total_autorizados >= empresa.max_equipos and not equipo.autorizado:
                raise HTTPException(
                    400, 
                    f"Se ha alcanzado el límite de {empresa.max_equipos} equipos autorizados para su empresa."
                )

        equipo.autorizado = body.autorizado
    
    if body.descripcion:
        equipo.descripcion = body.descripcion

    db.commit()
    db.refresh(equipo)
    
    accion = "autorizar_equipo" if body.autorizado else "desautorizar_equipo"
    registrar_audit(db, accion=accion, empresa_id=admin.empresa_id, usuario_id=admin.id,
                    entidad="equipo", entidad_id=str(equipo.id), 
                    detalle=f"Device:{equipo.device_id} Desc:{equipo.descripcion}")
    
    return equipo


@router.delete("/{equipo_id}", status_code=204)
def eliminar_equipo(
    equipo_id: int,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_admin_user),
):
    """
    Elimina un registro de equipo.
    """
    equipo = db.query(EquipoAutorizado).join(Usuario).filter(
        EquipoAutorizado.id == equipo_id,
        Usuario.empresa_id == admin.empresa_id
    ).first()
    
    if not equipo:
        raise HTTPException(404, "Equipo no encontrado")

    db.delete(equipo)
    db.commit()
    
    registrar_audit(db, accion="eliminar_equipo_rec", empresa_id=admin.empresa_id, usuario_id=admin.id,
                    entidad="equipo", entidad_id=str(equipo_id))
    return None
