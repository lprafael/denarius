from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Empresa, Emisor, Usuario
from app.schemas import EmpresaCreate, EmpresaOut, LoginIn, LoginOut, RefreshIn, CambioPasswordIn
from app.security import (
    autenticar_usuario, get_current_user,
    hash_password, iniciar_sesion, registrar_audit,
    crear_access_token, verificar_password, verificar_equipo,
)
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from app.config import settings
from app.schemas import (
    EmpresaCreate, EmpresaOut, LoginIn, LoginOut, 
    RefreshIn, CambioPasswordIn, GoogleLoginIn
)


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/registro-empresa", response_model=EmpresaOut, status_code=201)
def registrar_empresa(body: EmpresaCreate, request: Request, db: Session = Depends(get_db)):
    """Registra una nueva empresa habilitada en el sistema."""
    email_final = body.email_admin
    google_verified = False

    if body.google_token:
        try:
            id_info = id_token.verify_oauth2_token(
                body.google_token, 
                google_requests.Request(), 
                settings.google_client_id
            )
            email_final = id_info['email']
            google_verified = True
        except Exception as e:
            raise HTTPException(400, f"Token de Google inválido: {e}")

    if db.query(Empresa).filter(Empresa.nombre == body.nombre).first():
        raise HTTPException(400, "Ya existe una empresa con ese nombre")
    if db.query(Usuario).filter(Usuario.email == email_final).first():
        raise HTTPException(400, "El email de administrador ya está registrado")
    
    if not google_verified and not body.password_admin:
        raise HTTPException(400, "Debe proporcionar una contraseña o usar registro con Google")

    if db.query(Emisor).filter(Emisor.ruc_con_dv == body.ruc_con_dv).first():

        raise HTTPException(400, "El RUC ya está registrado")
    if "-" not in body.ruc_con_dv:
        raise HTTPException(400, "El RUC debe incluir dígito verificador, ej: 12345678-9")

    emp = Empresa(nombre=body.nombre, estado="pendiente")
    db.add(emp)
    db.flush()

    emisor = Emisor(
        empresa_id=emp.id,
        ruc_con_dv=body.ruc_con_dv,
        razon_social=body.razon_social,
        direccion=body.direccion,
        telefono=body.telefono,
        email=body.email,
    )
    db.add(emisor)

    # Si no hay password, se asume que usará Google (activo será False hasta aprobación)
    p_hash = hash_password(body.password_admin) if body.password_admin else f"GOOGLE_ONLY_{datetime.now(timezone.utc).timestamp()}"

    usr = Usuario(
        empresa_id=emp.id,
        email=email_final,
        nombre="Administrador (Solicitante)",
        password_hash=p_hash,
        rol="admin",
        activo=False,
    )

    db.add(usr)
    db.commit()

    db.refresh(emp)

    ip = request.client.host if request.client else ""
    registrar_audit(db, accion="registro_empresa", empresa_id=emp.id,
                    entidad="empresa", entidad_id=str(emp.id),
                    detalle=f"RUC:{body.ruc_con_dv}", ip=ip)
    return emp


@router.post("/login", response_model=LoginOut)
def login(body: LoginIn, request: Request, db: Session = Depends(get_db)):
    usr = autenticar_usuario(db, body.email, body.password)
    
    # Verificar restricción de equipo
    verificar_equipo(db, usr, body.device_id, request)
    
    access, refresh = iniciar_sesion(db, usr)
    empresa = db.query(Empresa).filter(Empresa.id == usr.empresa_id).first()

    ip = request.client.host if request.client else ""
    registrar_audit(db, accion="login", empresa_id=usr.empresa_id, usuario_id=usr.id,
                    entidad="usuario", entidad_id=str(usr.id), ip=ip)

    return LoginOut(
        access_token=access,
        refresh_token=refresh,
        empresa_id=usr.empresa_id,
        empresa_nombre=empresa.nombre if empresa else "",
        usuario_email=usr.email,
        rol=usr.rol,
    )


@router.post("/google-login", response_model=LoginOut)
def google_login(body: GoogleLoginIn, request: Request, db: Session = Depends(get_db)):
    """Inicio de sesión con Google OAuth2."""
    try:
        # 1. Verificar el token de Google
        id_info = id_token.verify_oauth2_token(
            body.credential, 
            google_requests.Request(), 
            settings.google_client_id
        )
        
        email = id_info['email']
        nombre = id_info.get('name', '')
        
        # 2. Buscar usuario por email
        usr = db.query(Usuario).filter(Usuario.email == email).first()
        
        if not usr:
            # Si no existe, error indicando que debe reportar su empresa primero
            raise HTTPException(401, "Su cuenta Google no está registrada. Por favor use el formulario de Registro de Empresa primero.")

        if not usr.activo:
            raise HTTPException(403, "Su solicitud de acceso aún está pendiente de aprobación por el SuperAdmin.")


        # 3. Verificar restricción de equipo
        verificar_equipo(db, usr, body.device_id, request)
        
        # 4. Iniciar sesión
        access, refresh = iniciar_sesion(db, usr)
        empresa = db.query(Empresa).filter(Empresa.id == usr.empresa_id).first()

        ip = request.client.host if request.client else ""
        registrar_audit(db, accion="login_google", empresa_id=usr.empresa_id, usuario_id=usr.id,
                        entidad="usuario", entidad_id=str(usr.id), ip=ip)

        return LoginOut(
            access_token=access,
            refresh_token=refresh,
            empresa_id=usr.empresa_id,
            empresa_nombre=empresa.nombre if empresa else "",
            usuario_email=usr.email,
            rol=usr.rol,
        )
        
    except ValueError as e:
        raise HTTPException(401, f"Token de Google inválido: {e}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error en autenticación Google: {str(e)}")



@router.post("/refresh", response_model=dict)
def refresh_token(body: RefreshIn, db: Session = Depends(get_db)):
    """Renueva el access token usando el refresh token."""
    usr = db.query(Usuario).filter(Usuario.refresh_token == body.refresh_token).first()
    if not usr or not usr.activo:
        raise HTTPException(401, "Refresh token inválido")
    if not usr.refresh_token_expira_at or usr.refresh_token_expira_at < datetime.now(timezone.utc).replace(tzinfo=None):
        raise HTTPException(401, "Refresh token expirado")
    access = crear_access_token(usr.id)
    return {"access_token": access, "token_type": "bearer"}


@router.post("/logout")
def logout(usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    """Invalida el refresh token activo."""
    usuario.refresh_token = ""
    usuario.refresh_token_expira_at = None
    db.commit()
    return {"ok": True}


@router.get("/me")
def me(usuario: Usuario = Depends(get_current_user)):
    return {
        "usuario_id": usuario.id,
        "email": usuario.email,
        "nombre": usuario.nombre,
        "rol": usuario.rol,
        "empresa_id": usuario.empresa_id,
    }


@router.post("/cambiar-password")
def cambiar_password(
    body: CambioPasswordIn,
    usuario: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verificar_password(body.password_actual, usuario.password_hash):
        raise HTTPException(400, "La contraseña actual es incorrecta")
    usuario.password_hash = hash_password(body.password_nuevo)
    # Invalidar refresh token por seguridad
    usuario.refresh_token = ""
    usuario.refresh_token_expira_at = None
    db.commit()
    return {"ok": True, "msg": "Contraseña actualizada exitosamente"}
