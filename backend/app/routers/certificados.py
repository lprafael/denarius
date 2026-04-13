from __future__ import annotations

import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives.serialization import pkcs12
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Certificado, Usuario
from app.schemas import CertificadoOut
from app.security import get_admin_user, registrar_audit

router = APIRouter(prefix="/api/certificados", tags=["certificados"])


def _extraer_info_cert(p12_data: bytes, password: str) -> dict:
    """Lee metadatos básicos del certificado."""
    try:
        _, cert, _ = pkcs12.load_key_and_certificates(
            p12_data, password.encode() if password else None
        )
        if cert is None:
            return {}
        numero_serie = str(cert.serial_number)
        fecha_venc = cert.not_valid_after_utc.replace(tzinfo=None)
        return {"numero_serie": numero_serie, "fecha_venc": fecha_venc}
    except Exception as e:
        raise HTTPException(400, f"No se pudo leer el certificado .p12: {e}") from e


@router.get("", response_model=list[CertificadoOut])
def listar(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_admin_user),
):
    return db.query(Certificado).filter(Certificado.empresa_id == usuario.empresa_id).all()


@router.post("", response_model=CertificadoOut, status_code=201)
def cargar(
    archivo: UploadFile = File(..., description="Certificado .p12"),
    alias: str = Form("principal"),
    password: str = Form(""),
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_admin_user),
):
    """Sube y registra un certificado PKCS#12 (.p12) para la empresa."""
    if not archivo.filename.endswith((".p12", ".pfx")):
        raise HTTPException(400, "Solo se aceptan archivos .p12 o .pfx")

    p12_data = archivo.file.read()
    info = _extraer_info_cert(p12_data, password)

    # Guardar el archivo en disco en carpeta segura
    store = Path(settings.cert_store_path) / str(admin.empresa_id)
    store.mkdir(parents=True, exist_ok=True)
    dest = store / archivo.filename
    dest.write_bytes(p12_data)

    # Desactivar certificados previos
    db.query(Certificado).filter(
        Certificado.empresa_id == admin.empresa_id
    ).update({"activo": False})

    cert = Certificado(
        empresa_id=admin.empresa_id,
        alias=alias,
        ruta_archivo=str(dest),
        numero_serie=info.get("numero_serie", ""),
        fecha_venc=info.get("fecha_venc"),
        activo=True,
    )
    db.add(cert)
    db.commit()
    db.refresh(cert)

    registrar_audit(db, accion="cargar_certificado", empresa_id=admin.empresa_id,
                    usuario_id=admin.id, entidad="certificado", entidad_id=str(cert.id),
                    detalle=f"alias:{alias} serie:{cert.numero_serie}")
    return cert


@router.delete("/{cert_id}", status_code=204)
def eliminar(
    cert_id: int,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(get_admin_user),
):
    c = db.query(Certificado).filter(Certificado.id == cert_id, Certificado.empresa_id == admin.empresa_id).first()
    if not c:
        raise HTTPException(404, "Certificado no encontrado")
    # Eliminar archivo
    try:
        Path(c.ruta_archivo).unlink(missing_ok=True)
    except Exception:
        pass
    db.delete(c)
    db.commit()
    registrar_audit(db, accion="eliminar_certificado", empresa_id=admin.empresa_id,
                    usuario_id=admin.id, entidad="certificado", entidad_id=str(cert_id))
