from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Inutilizacion, Emisor, Usuario
from app.schemas import InutilizacionCreate, InutilizacionOut
from app.security import get_admin_user, registrar_audit

router = APIRouter(prefix="/api/inutilizacion", tags=["inutilizacion"])


@router.get("", response_model=list[InutilizacionOut])
def listar(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_admin_user),
):
    return db.query(Inutilizacion).filter(Inutilizacion.empresa_id == usuario.empresa_id).order_by(Inutilizacion.id.desc()).all()


@router.post("", response_model=InutilizacionOut, status_code=201)
def crear(
    body: InutilizacionCreate,
    request: Request,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_admin_user),
):
    """
    Solicita la inutilización de un rango de numeración al SIFEN.
    Solo administradores pueden ejecutar esta acción.
    """
    if body.d_num_fin < body.d_num_ini:
        raise HTTPException(400, "d_num_fin debe ser mayor o igual a d_num_ini")

    emisor = db.query(Emisor).filter(Emisor.empresa_id == admin.empresa_id).first()
    if not emisor:
        raise HTTPException(400, "No hay emisor configurado")

    from app.models import Certificado
    cert = db.query(Certificado).filter(
        Certificado.empresa_id == admin.empresa_id, Certificado.activo == True
    ).order_by(Certificado.id.desc()).first()

    ruc_parts = emisor.ruc_con_dv.split("-")
    ruc_em = ruc_parts[0]
    dv_em = ruc_parts[1] if len(ruc_parts) > 1 else "0"

    from app.sifen.sifen_client import enviar_inutilizacion_firmada
    resultado = enviar_inutilizacion_firmada(
        num_timbrado=emisor.num_tim,
        d_est=body.d_est,
        d_pun_exp=body.d_pun_exp,
        d_num_ini=body.d_num_ini,
        d_num_fin=body.d_num_fin,
        i_ti_de=body.i_ti_de,
        motivo=body.motivo,
        ruc_emisor=ruc_em,
        dv_emisor=dv_em,
        p12_path=cert.ruta_archivo if cert else None,
        p12_password=cert.contrasena_enc if cert else "",
    )

    inu = Inutilizacion(
        empresa_id=admin.empresa_id,
        emisor_id=emisor.id,
        i_ti_de=body.i_ti_de,
        d_est=body.d_est,
        d_pun_exp=body.d_pun_exp,
        d_num_ini=body.d_num_ini,
        d_num_fin=body.d_num_fin,
        motivo=body.motivo,
        xml_inutilizacion=resultado.get("xml_inutilizacion", ""),
        estado="aprobado" if resultado.get("aprobado") else "rechazado",
        sifen_respuesta=resultado.get("raw", "")[:4000],
    )
    db.add(inu)
    db.commit()
    db.refresh(inu)

    ip = request.client.host if request.client else ""
    registrar_audit(db, accion="inutilizacion", empresa_id=admin.empresa_id, usuario_id=admin.id,
                    entidad="inutilizacion", entidad_id=str(inu.id),
                    detalle=f"est:{body.d_est} rango:{body.d_num_ini}-{body.d_num_fin}", ip=ip)
    return inu
