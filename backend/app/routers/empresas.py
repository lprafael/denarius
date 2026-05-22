from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from sqlalchemy import func
from app.database import get_db
from app.models import Empresa, Usuario, Emisor, Factura

from app.schemas import EmpresaOut, EmpresaEmailUpdate, PasswordResetRequest
from app.security import get_admin_user, get_current_user, hash_password, registrar_audit
from pydantic import BaseModel
from fastapi import Request, UploadFile, File
import os
import shutil

router = APIRouter(prefix="/api/empresas", tags=["empresas"])

@router.get("/dashboard", response_model=dict)
def get_superadmin_dashboard(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_admin_user)
):
    """Retorna estadísticas globales del sistema para el SuperAdmin."""
    if usuario.rol != "superadmin":
        raise HTTPException(status_code=403, detail="No tienes permisos para ver el dashboard global")
    
    total_empresas = db.query(Empresa).count()
    # Contar activas (manejando tanto 'activo' como 'activa')
    empresas_activas = db.query(Empresa).filter(Empresa.estado.in_(['activo', 'activa'])).count()

    
    # Empresas operativas (con al menos 1 factura)
    empresas_operativas = db.query(Factura.empresa_id).distinct().count()
    
    total_facturas = db.query(Factura).count()
    total_monto = db.query(func.sum(Factura.d_tot_gral_ope)).scalar() or 0
    
    # Detalle por empresa
    stats_por_empresa = db.query(
        Empresa.id,
        Empresa.nombre,
        Empresa.estado,
        func.count(Factura.id).label("facturas_count"),
        func.sum(Factura.d_tot_gral_ope).label("monto_total")
    ).outerjoin(Factura, Empresa.id == Factura.empresa_id).group_by(Empresa.id, Empresa.nombre, Empresa.estado).all()
    
    detalle = []
    for s in stats_por_empresa:
        # Buscar RUC
        em = db.query(Emisor).filter(Emisor.empresa_id == s.id).first()
        detalle.append({
            "empresa_id": s.id,
            "nombre": s.nombre,
            "ruc": em.ruc_con_dv if em else "N/A",
            "estado": s.estado,
            "cantidad_facturas": s.facturas_count,
            "total_monto": float(s.monto_total or 0)
        })
        
    return {
        "total_empresas": total_empresas,
        "empresas_activas": empresas_activas,
        "empresas_operativas": empresas_operativas,
        "total_facturas": total_facturas,
        "monto_total_general": float(total_monto or 0),
        "detalle_empresas": detalle
    }



@router.get("", response_model=List[dict])
def listar_empresas(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_admin_user)
):
    """Solo SuperAdmin puede ver todas las empresas del sistema."""
    if usuario.rol != "superadmin":
        raise HTTPException(status_code=403, detail="No tienes permisos para ver el listado global")
    
    empresas = db.query(Empresa).all()
    result = []
    for emp in empresas:
        emisor = db.query(Emisor).filter(Emisor.empresa_id == emp.id).first()
        result.append({
            "id": emp.id,
            "nombre": emp.nombre,
            "ruc": emisor.ruc_con_dv if emisor else "SIN RUC",
            "razon_social": emisor.razon_social if emisor else "SIN RAZON",
            "estado": emp.estado,
            "plantilla_kude": getattr(emp, 'plantilla_kude', 'kude_ticket.html'),
            "restriccion_equipos": emp.restriccion_equipos,
            "max_equipos": emp.max_equipos,
            "email_admin": emp.email_admin,
            "created_at": emp.created_at

        })
    return result

@router.put("/{empresa_id}/toggle", response_model=dict)
def toggle_empresa(
    empresa_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_admin_user)
):
    """Permite al SuperAdmin activar o desactivar una empresa."""
    if usuario.rol != "superadmin":
        raise HTTPException(403, "Sin permisos")
    
    emp = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not emp: raise HTTPException(404, "Empresa no encontrada")
    
    # PROTECCIÓN: Si el SuperAdmin pertenece a esta empresa, no puede desactivarla él mismo
    if usuario.empresa_id == empresa_id:
        raise HTTPException(status_code=400, detail="No puedes deshabilitar la empresa a la que perteneces")
    
    nuevo_estado = "inactivo" if emp.estado in ["activo", "activa"] else "activo"
    emp.estado = nuevo_estado
    
    # Sincronizar estado de activación de usuarios de la empresa
    for u in emp.usuarios:
        u.activo = (nuevo_estado == "activo")

    db.commit()
    return {"id": emp.id, "nombre": emp.nombre, "nuevo_estado": emp.estado}



@router.delete("/{empresa_id}")
def eliminar_empresa(
    empresa_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_admin_user)
):
    """Elimina una empresa y todos sus datos asociados."""
    if usuario.rol != "superadmin":
        raise HTTPException(403, "Sin permisos")
    
    emp = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not emp: raise HTTPException(404, "Empresa no encontrada")
    
    db.delete(emp)
    db.commit()
    return {"ok": True, "detail": f"Empresa {empresa_id} eliminada con éxito"}

class EmpresaUpdate(BaseModel):
    nombre: str | None = None
    razon_social: str | None = None
    ruc_con_dv: str | None = None
    plantilla_kude: str | None = None
    restriccion_equipos: bool | None = None
    max_equipos: int | None = None


@router.put("/{empresa_id}", response_model=dict)
def modificar_empresa(
    empresa_id: int,
    body: EmpresaUpdate,
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_admin_user)
):
    """Permite al SuperAdmin modificar datos de una empresa. Queda registrado en la auditoría."""
    if usuario.rol != "superadmin":
        raise HTTPException(status_code=403, detail="Sin permisos")
    
    emp = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not emp: raise HTTPException(status_code=404, detail="Empresa no encontrada")

    cambios = []
    if body.nombre and body.nombre != emp.nombre:
        cambios.append(f"Nombre: {emp.nombre} -> {body.nombre}")
        emp.nombre = body.nombre
    
    # Manejar atributo plantilla_kude dinámicamente si no está en todos los entornos
    plantilla_actual = getattr(emp, 'plantilla_kude', None)
    if body.plantilla_kude is not None and body.plantilla_kude != plantilla_actual:
        cambios.append(f"Plantilla: {plantilla_actual} -> {body.plantilla_kude}")
        if hasattr(emp, 'plantilla_kude'):
            emp.plantilla_kude = body.plantilla_kude

    emisor = db.query(Emisor).filter(Emisor.empresa_id == emp.id).first()
    if emisor:
        if body.razon_social and body.razon_social != emisor.razon_social:
            cambios.append(f"Razón: {emisor.razon_social} -> {body.razon_social}")
            emisor.razon_social = body.razon_social
        if body.ruc_con_dv and body.ruc_con_dv != emisor.ruc_con_dv:
            cambios.append(f"RUC: {emisor.ruc_con_dv} -> {body.ruc_con_dv}")
            emisor.ruc_con_dv = body.ruc_con_dv
    
    if body.restriccion_equipos is not None and body.restriccion_equipos != emp.restriccion_equipos:
        cambios.append(f"Restricción Equipos: {emp.restriccion_equipos} -> {body.restriccion_equipos}")
        emp.restriccion_equipos = body.restriccion_equipos

    if body.max_equipos is not None and body.max_equipos != emp.max_equipos:
        cambios.append(f"Max Equipos: {emp.max_equipos} -> {body.max_equipos}")
        emp.max_equipos = body.max_equipos

    
    db.commit()

    if cambios:
        registrar_audit(
            db,
            accion="modificar_empresa_superadmin",
            empresa_id=empresa_id,
            usuario_id=usuario.id,
            entidad="empresa",
            entidad_id=str(empresa_id),
            detalle=", ".join(cambios),
            ip=request.client.host if request.client else ""
        )

    return {"ok": True, "cambios": cambios}

@router.post("/admins", response_model=dict)
def crear_superadmin(
    nombre: str,
    email: str,
    password: str,
    db: Session = Depends(get_db),
    usuario_req: Usuario = Depends(get_admin_user)
):
    """Permite a un SuperAdmin crear otro SuperAdmin."""
    if usuario_req.rol != "superadmin":
        raise HTTPException(403, "Sin permisos")
    
    # Verificar si ya existe
    exist = db.query(Usuario).filter(Usuario.email == email).first()
    if exist: raise HTTPException(400, "El email ya está registrado")
    
    nuevo = Usuario(
        nombre=nombre,
        email=email,
        hashed_password=hash_password(password),
        rol="superadmin",
        empresa_id=None # Los superadmins no pertenecen a una empresa específica
    )
    db.add(nuevo)
    db.commit()
    return {"ok": True, "email": email, "rol": "superadmin"}

@router.post("/me/logo", response_model=dict)
def upload_logo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    """Sube el logo para la empresa del usuario actual"""
    emp = db.query(Empresa).filter(Empresa.id == usuario.empresa_id).first()
    if not emp:
        raise HTTPException(404, "Empresa no encontrada")
        
    os.makedirs("uploads/logos", exist_ok=True)
    file_path = f"uploads/logos/empresa_{emp.id}_{file.filename}"
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Guardar ruta (podría ser relativa para que el frontend la lea si se sirve como estático)
    # Por ahora la guardamos como base64 o como ruta que luego expondremos.
    # Dado que generar base64 es más portable para incrustar en PDFs y HTMLs locales sin conf de estáticos:
    with open(file_path, "rb") as image_file:
        import base64
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        
    # Guardamos el base64 directamente en la DB para no lidiar con servir estáticos en este proyecto si no están configurados.
    emp.logo_url = f"data:{file.content_type};base64,{encoded_string}"
    db.commit()
    
    return {"ok": True, "logo_url": emp.logo_url}

@router.get("/me/logo", response_model=dict)
def get_logo(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    emp = db.query(Empresa).filter(Empresa.id == usuario.empresa_id).first()
    return {"logo_url": emp.logo_url if emp else ""}

@router.put("/admin-email/{empresa_id}", response_model=dict)
def update_admin_email(
    empresa_id: int,
    payload: EmpresaEmailUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_admin_user),
):
    """Actualiza el email del administrador de la empresa. Solo SuperAdmin."""
    if usuario.rol != "superadmin":
        raise HTTPException(status_code=403, detail="Sin permisos")
    emp = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    emp.email_admin = payload.email_admin
    db.commit()
    registrar_audit(
        db,
        accion="update_admin_email",
        empresa_id=empresa_id,
        usuario_id=usuario.id,
        entidad="empresa",
        entidad_id=str(empresa_id),
        detalle=f"Email admin actualizado a {payload.email_admin}",
        ip="",
    )
    return {"ok": True, "email_admin": emp.email_admin}

@router.post("/admin-email/{empresa_id}/reset-password", response_model=dict)
def reset_admin_password(
    empresa_id: int,
    payload: PasswordResetRequest,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_admin_user),
):
    """Genera token de reset y envía email al admin. Solo SuperAdmin."""
    if usuario.rol != "superadmin":
        raise HTTPException(status_code=403, detail="Sin permisos")
    emp = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    if payload.email_admin != emp.email_admin:
        raise HTTPException(status_code=400, detail="El email no coincide con el registrado")
    import uuid, datetime
    from datetime import timedelta
    token = str(uuid.uuid4())
    # Guardar token en tabla PasswordReset
    from app.models import PasswordReset
    reset = PasswordReset(
        empresa_id=empresa_id,
        token=token,
        created_at=datetime.datetime.utcnow(),
        expira_at=datetime.datetime.utcnow() + timedelta(hours=24),
    )
    db.add(reset)
    db.commit()
    # Envío de email en background
    from app.email_utils import send_password_reset
    background.add_task(send_password_reset, email_to=emp.email_admin, token=token)
    return {"ok": True, "msg": "Email de reset enviado"}
