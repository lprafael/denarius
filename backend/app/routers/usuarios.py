from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Usuario
from app.schemas import UsuarioCreate, UsuarioOut, UsuarioUpdate
from app.security import get_admin_user, get_current_user, hash_password, registrar_audit

router = APIRouter(prefix="/api/usuarios", tags=["usuarios"])


@router.get("", response_model=list[UsuarioOut])
def listar(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_admin_user),
):
    """Lista todos los usuarios de la empresa (solo admin)."""
    return db.query(Usuario).filter(Usuario.empresa_id == usuario.empresa_id).all()


@router.get("/{usuario_id}", response_model=UsuarioOut)
def obtener(
    usuario_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_admin_user),
):
    u = db.query(Usuario).filter(Usuario.id == usuario_id, Usuario.empresa_id == usuario.empresa_id).first()
    if not u:
        raise HTTPException(404, "Usuario no encontrado")
    return u


@router.post("", response_model=UsuarioOut, status_code=201)
def crear(
    body: UsuarioCreate,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_admin_user),
):
    """Crea un nuevo usuario bajo la misma empresa del administrador."""
    if db.query(Usuario).filter(Usuario.email == body.email).first():
        raise HTTPException(400, "El email ya está registrado")
    nuevo = Usuario(
        empresa_id=admin.empresa_id,
        email=body.email,
        nombre=body.nombre,
        password_hash=hash_password(body.password),
        rol=body.rol,
        activo=True,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    registrar_audit(db, accion="crear_usuario", empresa_id=admin.empresa_id, usuario_id=admin.id,
                    entidad="usuario", entidad_id=str(nuevo.id), detalle=f"email:{body.email} rol:{body.rol}")
    return nuevo


@router.put("/{usuario_id}", response_model=UsuarioOut)
def actualizar(
    usuario_id: int,
    body: UsuarioUpdate,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_admin_user),
):
    u = db.query(Usuario).filter(Usuario.id == usuario_id, Usuario.empresa_id == admin.empresa_id).first()
    if not u:
        raise HTTPException(404, "Usuario no encontrado")
    for field, value in body.model_dump(exclude_none=True).items():
        if field == "activo" and value is False and u.id == admin.id:
            raise HTTPException(400, "No puede deshabilitarse a sí mismo")
        setattr(u, field, value)
    db.commit()
    db.refresh(u)
    registrar_audit(db, accion="actualizar_usuario", empresa_id=admin.empresa_id, usuario_id=admin.id,
                    entidad="usuario", entidad_id=str(u.id))
    return u


@router.delete("/{usuario_id}", status_code=204)
def deshabilitar(
    usuario_id: int,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_admin_user),
):
    u = db.query(Usuario).filter(Usuario.id == usuario_id, Usuario.empresa_id == admin.empresa_id).first()
    if not u:
        raise HTTPException(404, "Usuario no encontrado")
    if u.id == admin.id:
        raise HTTPException(400, "No puede deshabilitarse a sí mismo")
    u.activo = False
    u.refresh_token = ""
    db.commit()
    registrar_audit(db, accion="deshabilitar_usuario", empresa_id=admin.empresa_id, usuario_id=admin.id,
                    entidad="usuario", entidad_id=str(u.id))
