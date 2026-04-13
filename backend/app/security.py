from __future__ import annotations

import bcrypt
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import AuditLog, Usuario, Empresa, EquipoAutorizado


bearer = HTTPBearer(auto_error=False)

# Segundos de bloqueo por intentos fallidos
LOCK_MINUTES = 15
MAX_INTENTOS = 5


# ---------------------------------------------------------------------------
# Contraseñas con bcrypt
# ---------------------------------------------------------------------------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()

# Alias de compatibilidad
get_password_hash = hash_password


def verificar_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False


# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------
def _crear_token(sub: str, tipo: str, expire_delta: timedelta) -> str:
    ahora = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "tipo": tipo,
        "iat": ahora,
        "exp": ahora + expire_delta,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def crear_access_token(usuario_id: int) -> str:
    return _crear_token(
        str(usuario_id),
        "access",
        timedelta(minutes=settings.jwt_access_expire_minutes),
    )


def crear_refresh_token() -> str:
    return secrets.token_urlsafe(64)


def decodificar_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Token inválido: {e}") from e


# ---------------------------------------------------------------------------
# Autenticación
# ---------------------------------------------------------------------------
def autenticar_usuario(db: Session, email: str, password: str) -> Usuario:
    usr = db.query(Usuario).filter(Usuario.email == email).first()
    if not usr:
        raise HTTPException(401, "Credenciales inválidas")
    if not usr.activo:
        raise HTTPException(403, "Usuario deshabilitado")
    # Verificar bloqueo temporal
    if usr.bloqueado_hasta and usr.bloqueado_hasta > datetime.now(timezone.utc).replace(tzinfo=None):
        raise HTTPException(423, f"Cuenta bloqueada temporalmente. Intente después de {usr.bloqueado_hasta.isoformat()}")
    if not verificar_password(password, usr.password_hash):
        usr.intentos_fallidos += 1
        if usr.intentos_fallidos >= MAX_INTENTOS:
            usr.bloqueado_hasta = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=LOCK_MINUTES)
            usr.intentos_fallidos = 0
        db.commit()
        raise HTTPException(401, "Credenciales inválidas")
    # Login exitoso: resetear contadores
    usr.intentos_fallidos = 0
    usr.bloqueado_hasta = None
    db.commit()
    return usr


def iniciar_sesion(db: Session, usr: Usuario) -> tuple[str, str]:
    access = crear_access_token(usr.id)
    refresh = crear_refresh_token()
    usr.refresh_token = refresh
    usr.refresh_token_expira_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
        days=settings.jwt_refresh_expire_days
    )
    db.commit()
    return access, refresh


# ---------------------------------------------------------------------------
# Dependency: usuario autenticado actual
# ---------------------------------------------------------------------------
def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> Usuario:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Token requerido")
    payload = decodificar_access_token(credentials.credentials)
    usuario_id = int(payload.get("sub", 0))
    usr = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usr or not usr.activo:
        raise HTTPException(status_code=401, detail="Usuario inválido o inactivo")
    return usr


def get_admin_user(usr: Usuario = Depends(get_current_user)) -> Usuario:
    if usr.rol not in ("admin", "superadmin"):
        raise HTTPException(status_code=403, detail="Se requiere rol administrador")
    return usr


# ---------------------------------------------------------------------------
# Escritura de auditoría
# ---------------------------------------------------------------------------
def registrar_audit(
    db: Session,
    *,
    accion: str,
    empresa_id: int | None = None,
    usuario_id: int | None = None,
    entidad: str = "",
    entidad_id: str = "",
    detalle: str = "",
    ip: str = "",
) -> None:
    log = AuditLog(
        empresa_id=empresa_id,
        usuario_id=usuario_id,
        accion=accion,
        entidad=entidad,
        entidad_id=entidad_id,
        detalle=detalle,
        ip=ip,
    )
    db.add(log)
    db.commit()


# ---------------------------------------------------------------------------
# Verificación de Equipos
# ---------------------------------------------------------------------------
def verificar_equipo(
    db: Session, 
    usuario: Usuario, 
    device_id: str | None, 
    request: Request
) -> bool:
    """
    Verifica si el equipo está autorizado.
    Si no está autorizado y el usuario/empresa tiene restricción, lanza HTTPException 403.
    Si no existe registro del equipo, lo crea como 'pendiente' (autorizado=False).
    """
    # 1. Obtener la empresa para ver si tiene restricción global
    empresa = db.query(Empresa).filter(Empresa.id == usuario.empresa_id).first()
    
    # 2. Si ni la empresa ni el usuario tienen restricción, permitir acceso
    if not empresa.restriccion_equipos and not usuario.restriccion_equipo:
        return True

    # 3. Si hay restricción pero no se envió device_id, bloquear
    if not device_id:
        raise HTTPException(
            status_code=403, 
            detail="Este usuario requiere inicio de sesión desde un equipo autorizado, pero no se detectó el identificador del equipo."
        )

    # 4. Buscar el equipo en la base de datos
    equipo = db.query(EquipoAutorizado).filter(
        EquipoAutorizado.usuario_id == usuario.id,
        EquipoAutorizado.device_id == device_id
    ).first()

    if not equipo:
        # Registrar como nuevo equipo pendiente de autorización
        nuevo_equipo = EquipoAutorizado(
            usuario_id=usuario.id,
            device_id=device_id,
            descripcion="Solicitud de Acceso",
            ip_registro=request.client.host if request.client else "",
            user_agent=request.headers.get("user-agent", ""),
            autorizado=False
        )
        db.add(nuevo_equipo)
        db.commit()
        raise HTTPException(
            status_code=403, 
            detail="Este equipo no está autorizado. Se ha enviado una solicitud de habilitación al administrador de su empresa."
        )

    if not equipo.autorizado:
        raise HTTPException(
            status_code=403, 
            detail="Su solicitud de acceso para este equipo aún está pendiente de aprobación."
        )

    return True

