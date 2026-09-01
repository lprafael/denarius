from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Certificado, Emisor, EstadoEnvioDE, Factura, LoteDE, Usuario
from app.security import get_current_user, registrar_audit
from app.sifen.sifen_client import consultar_lote, enviar_lote_asincrono

router = APIRouter(prefix="/api/lotes", tags=["lotes"])


class EnviarLoteRequest(BaseModel):
    factura_ids: list[int] = Field(..., min_length=1, max_length=50)
    cert_password: str = ""


@router.get("")
def listar_lotes(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """Lista el historial de lotes enviados por la empresa."""
    q = db.query(LoteDE).filter(LoteDE.empresa_id == usuario.empresa_id)
    return q.order_by(LoteDE.id.desc()).offset(skip).limit(limit).all()


@router.get("/{lote_id}")
def obtener_lote(
    lote_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """Obtiene el detalle de un lote y sus documentos contenidos."""
    lote = db.query(LoteDE).filter(LoteDE.id == lote_id, LoteDE.empresa_id == usuario.empresa_id).first()
    if not lote:
        raise HTTPException(404, "Lote no encontrado")

    facturas = db.query(Factura).filter(Factura.lote_id == lote.id).all()
    return {
        "lote": lote,
        "facturas": [
            {
                "id": f.id,
                "cdc": f.cdc,
                "numero_documento": f.numero_documento,
                "receptor_nombre": f.receptor_nombre,
                "total": f.d_tot_gral_ope,
                "estado_envio": f.estado_envio,
                "sifen_protocolo": f.sifen_protocolo,
            }
            for f in facturas
        ],
    }


@router.post("/enviar")
def crear_y_enviar_lote(
    body: EnviarLoteRequest,
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """
    Empaqueta hasta 50 DEs firmados en un lote comprimido ZIP y lo envía al servicio web asíncrono.
    """
    facturas = (
        db.query(Factura)
        .filter(Factura.id.in_(body.factura_ids), Factura.empresa_id == usuario.empresa_id)
        .all()
    )
    if not facturas:
        raise HTTPException(400, "No se encontraron facturas válidas")

    # Regla SIFEN: Mismo tipo de documento por lote
    tipos_de = {f.i_ti_de for f in facturas}
    if len(tipos_de) > 1:
        raise HTTPException(
            400, "Regla SIFEN: Todos los documentos de un lote deben ser del mismo tipo (ej: solo Facturas o solo Notas de Crédito)"
        )

    tipo_doc = list(tipos_de)[0]

    # Verificar que todos tengan XML firmado
    xmls_firmados = []
    for f in facturas:
        if not f.xml_firmado:
            raise HTTPException(400, f"La factura con CDC {f.cdc} no ha sido firmada digitalmente")
        xmls_firmados.append(f.xml_firmado)

    # Certificado
    cert = (
        db.query(Certificado)
        .filter(Certificado.empresa_id == usuario.empresa_id, Certificado.activo == True)
        .order_by(Certificado.id.desc())
        .first()
    )
    p12_path = cert.ruta_archivo if cert else None
    p12_pwd = body.cert_password or (cert.contrasena_enc if cert else "")

    # Enviar al WS asíncrono
    resultado = enviar_lote_asincrono(
        lista_xml_firmados=xmls_firmados,
        p12_path=p12_path,
        p12_password=p12_pwd,
    )

    estado_lote = "encolado" if resultado.get("encolado") else "rechazado"
    lote = LoteDE(
        empresa_id=usuario.empresa_id,
        i_ti_de=tipo_doc,
        d_prot_cons_lote=resultado.get("protocolo_lote", ""),
        cantidad_de=len(facturas),
        estado=estado_lote,
        sifen_cod_res=resultado.get("codigo", ""),
        sifen_msg_res=resultado.get("mensaje", ""),
        sifen_respuesta_raw=resultado.get("raw", "")[:4000],
        xml_lote_zip_b64=resultado.get("zip_b64", ""),
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(lote)
    db.flush()

    # Asociar facturas al lote y actualizar estado
    for f in facturas:
        f.lote_id = lote.id
        if resultado.get("encolado"):
            f.estado_envio = EstadoEnvioDE.enviado
        else:
            f.estado_envio = EstadoEnvioDE.rechazado
            f.sifen_respuesta = resultado.get("mensaje", "")

    db.commit()
    db.refresh(lote)

    registrar_audit(
        db,
        accion="enviar_lote_asincrono",
        empresa_id=usuario.empresa_id,
        usuario_id=usuario.id,
        entidad="lote_de",
        entidad_id=str(lote.id),
        detalle=f"Protocolo:{lote.d_prot_cons_lote} Cantidad:{len(facturas)}",
        ip=request.client.host if request.client else "",
    )

    return {
        "ok": True,
        "lote_id": lote.id,
        "protocolo": lote.d_prot_cons_lote,
        "estado": lote.estado,
        "mensaje": lote.sifen_msg_res,
        "cantidad": len(facturas),
    }


@router.post("/{lote_id}/consultar")
def consultar_estado_lote_sifen(
    lote_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """
    Consulta el resultado de procesamiento del lote a SIFEN (intervalo recomendado >= 10 min).
    Actualiza el estado de cada factura individualmente según la respuesta de SIFEN.
    """
    lote = db.query(LoteDE).filter(LoteDE.id == lote_id, LoteDE.empresa_id == usuario.empresa_id).first()
    if not lote:
        raise HTTPException(404, "Lote no encontrado")
    if not lote.d_prot_cons_lote:
        raise HTTPException(400, "El lote no cuenta con número de protocolo para consulta")

    cert = (
        db.query(Certificado)
        .filter(Certificado.empresa_id == usuario.empresa_id, Certificado.activo == True)
        .order_by(Certificado.id.desc())
        .first()
    )
    p12_path = cert.ruta_archivo if cert else None
    p12_pwd = cert.contrasena_enc if cert else ""

    res = consultar_lote(
        d_prot_cons_lote=lote.d_prot_cons_lote,
        p12_path=p12_path,
        p12_password=p12_pwd,
    )

    lote.consultado_at = datetime.now(timezone.utc).replace(tzinfo=None)
    lote.sifen_cod_res = res.get("codigo_lote", "")
    lote.sifen_msg_res = res.get("mensaje_lote", "")
    lote.sifen_respuesta_raw = res.get("raw", "")[:4000]

    # Si concluyó el procesamiento
    if res.get("codigo_lote") == "0362":
        lote.estado = "concluido"
        # Actualizar cada factura según su resultado
        docs_map = {d["cdc"]: d for d in res.get("documentos", [])}
        facturas = db.query(Factura).filter(Factura.lote_id == lote.id).all()
        for f in facturas:
            info = docs_map.get(f.cdc)
            if info:
                f.sifen_protocolo = info.get("protocolo_autorizacion", "")
                f.sifen_respuesta = f"{info.get('codigo_resultado', '')}: {info.get('mensaje_resultado', '')}"
                if info.get("estado") in ("Aprobado", "Aprobado con observación"):
                    f.estado_envio = EstadoEnvioDE.aprobado
                else:
                    f.estado_envio = EstadoEnvioDE.rechazado
    elif res.get("codigo_lote") == "0361":
        lote.estado = "en_procesamiento"

    db.commit()
    db.refresh(lote)

    return {
        "ok": True,
        "codigo_lote": lote.sifen_cod_res,
        "mensaje_lote": lote.sifen_msg_res,
        "estado": lote.estado,
        "documentos_procesados": res.get("documentos", []),
    }
