from __future__ import annotations

import hashlib
from urllib.parse import urlencode

from app.config import settings


def _fe_emi_hex(fecha_iso: str) -> str:
    """dFeEmiDE en el QR: cadena UTF-8 del datetime en hexadecimal (como en ejemplos e-Kuatia)."""
    return fecha_iso.encode("utf-8").hex()


def construir_d_car_qr(
    *,
    cdc: str,
    d_fe_emi_de: str,
    d_ruc_rec: str,
    d_tot_gral_ope: int,
    d_tot_iva: int,
    c_items: int,
    digest_value_base64: str,
    id_csc: str | None = None,
    csc_secreto: str | None = None,
) -> str:
    """
    URL del código QR (campo dCarQR). 
    cHashQR: SHA-256 en hex sobre la concatenación de los parámetros de la URL + CSC.
    """
    id_csc = id_csc or settings.id_csc_default
    sec = csc_secreto or settings.csc_secreto
    fe_hex = _fe_emi_hex(d_fe_emi_de)
    
    # El DigestValue en el QR debe ser la representación hexadecimal de la cadena Base64 del digest
    digest_value_param = digest_value_base64.encode("utf-8").hex()

    # Parámetros para la URL (orden importa para el hash según manual)
    params = [
        ("nVersion", str(settings.d_ver_for)),
        ("Id", cdc),
        ("dFeEmiDE", fe_hex),
        ("dRucRec", d_ruc_rec),
        ("dTotGralOpe", str(d_tot_gral_ope)),
        ("dTotIVA", str(d_tot_iva)),
        ("cItems", str(c_items)),
        ("DigestValue", digest_value_param),
        ("IdCSC", id_csc),
    ]
    
    # Construir cadena para hash: nVersion + Id + ... + IdCSC + CSC
    payload = "".join(v for k, v in params) + sec
    c_hash_qr = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    # Añadir el hash al final de los parámetros
    params.append(("cHashQR", c_hash_qr))
    
    query_string = urlencode(params)
    return f"{settings.qr_base_url}?{query_string}"


def digest_placeholder_para_qr(cdc: str, d_fe_emi_de: str) -> str:
    """Digest en hex para parámetro DigestValue hasta contar con firma XML real (SHA-256 del DE firmado)."""
    return hashlib.sha256(f"{cdc}|{d_fe_emi_de}".encode("utf-8")).hexdigest()
