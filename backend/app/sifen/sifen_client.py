"""
Cliente SIFEN — Webservices SET Paraguay (v150).

Implementa:
- Envío de Lote DE (recepción síncrona).
- Consulta de estado de DE por CDC.
- Envío de Eventos (cancelación, inutilización, etc.).

Los endpoints SOAP de SET reciben un envelope XML con autenticación
mediante el certificado digital del contribuyente.

Referencia: Especificación Técnica para Integración SIFEN e-Kuatia Paraguay.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
from cryptography.hazmat.primitives.serialization import pkcs12
from lxml import etree

from app.config import settings


TIMEOUT = 60  # segundos


def _get_ws_url(servicio: str) -> str:
    """Retorna URL del WS según ambiente configurado."""
    amb = settings.sifen_ambiente
    mapa = {
        "recepcion": settings.sifen_ws_url_test if amb == "test" else settings.sifen_ws_url_prod,
        "consulta": settings.sifen_ws_consulta_test if amb == "test" else settings.sifen_ws_consulta_prod,
        "eventos": settings.sifen_ws_eventos_test if amb == "test" else settings.sifen_ws_eventos_prod,
        "inutilizacion": settings.sifen_ws_inutilizacion_test if amb == "test" else settings.sifen_ws_inutilizacion_prod,
    }
    return mapa[servicio]


def _soap_envelope(body_content: str) -> str:
    """Construye un SOAP 1.2 envelope."""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"
               xmlns:xsd="http://www.w3.org/2001/XMLSchema">
  <soap:Header/>
  <soap:Body>
    {body_content}
  </soap:Body>
</soap:Envelope>"""


def _parse_respuesta_sifen(response_text: str) -> dict:
    """Parsea la respuesta SOAP de SIFEN y extrae los campos clave."""
    try:
        root = etree.fromstring(response_text.encode("utf-8"))
        # Buscar dCodRes (código de respuesta) y dMsgRes (mensaje)
        ns_sifen = "http://ekuatia.set.gov.py/sifen/xsd"
        cod = root.find(f".//{{{ns_sifen}}}dCodRes")
        msg = root.find(f".//{{{ns_sifen}}}dMsgRes")
        protocolo = root.find(f".//{{{ns_sifen}}}dProtAut")
        return {
            "codigo": cod.text if cod is not None else "",
            "mensaje": msg.text if msg is not None else response_text[:500],
            "protocolo": protocolo.text if protocolo is not None else "",
            "raw": response_text,
        }
    except Exception:
        return {"codigo": "", "mensaje": response_text[:500], "protocolo": "", "raw": response_text}


def enviar_lote_de(
    xml_firmado: str,
    cdc: str,
    p12_path: str | None = None,
    p12_password: str | None = None,
) -> dict:
    """
    Envía un Documento Electrónico firmado al WS de recepción síncrona de SIFEN.
    
    Returns:
        dict con: codigo, mensaje, protocolo, raw, aprobado (bool).
    """
    url = _get_ws_url("recepcion")

    body = f"""<rEnviDe xmlns="http://ekuatia.set.gov.py/sifen/xsd">
      <xDE>{xml_firmado}</xDE>
    </rEnviDe>"""

    envelope = _soap_envelope(body)

    headers = {
        "Content-Type": "application/soap+xml; charset=utf-8",
    }

    try:
        # Configurar cliente con certificado mTLS
        client_kwargs: dict = {"timeout": TIMEOUT, "verify": True}

        if p12_path and Path(p12_path).exists():
            # httpx no soporta .p12 directamente. Extraemos cert+key en PEM temporalmente.
            try:
                import tempfile
                import os
                from cryptography.hazmat.primitives.serialization import (
                    Encoding, PrivateFormat, NoEncryption
                )
                p12_data = Path(p12_path).read_bytes()
                _pwd = p12_password.encode() if p12_password else None
                _key, _cert, _ = pkcs12.load_key_and_certificates(p12_data, _pwd)

                with tempfile.NamedTemporaryFile(suffix=".pem", delete=False) as cert_pem, \
                     tempfile.NamedTemporaryFile(suffix=".pem", delete=False) as key_pem:
                    cert_pem.write(_cert.public_bytes(Encoding.PEM))
                    key_pem.write(_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()))
                    cert_pem_path = cert_pem.name
                    key_pem_path = key_pem.name

                client_kwargs["cert"] = (cert_pem_path, key_pem_path)
                _temp_files = (cert_pem_path, key_pem_path)
            except Exception:
                _temp_files = ()
        else:
            _temp_files = ()

        with httpx.Client(**client_kwargs) as client:
            resp = client.post(url, content=envelope.encode("utf-8"), headers=headers)
            resp.raise_for_status()
            resultado = _parse_respuesta_sifen(resp.text)
    except httpx.HTTPStatusError as e:
        return {"codigo": str(e.response.status_code), "mensaje": str(e), "protocolo": "", "raw": "", "aprobado": False}
    except Exception as e:
        return {"codigo": "ERR", "mensaje": str(e), "protocolo": "", "raw": "", "aprobado": False}
    finally:
        # Limpiar archivos PEM temporales
        import os as _os
        for _f in _temp_files:
            try:
                _os.unlink(_f)
            except Exception:
                pass

    # Código 0300 = aprobado según especificación SET
    resultado["aprobado"] = resultado.get("codigo") == "0300"
    return resultado


def consultar_estado_de(cdc: str) -> dict:
    """
    Consulta el estado de un DE en SIFEN por su CDC.
    
    Returns:
        dict con: codigo, mensaje, protocolo, raw, estado (str).
    """
    url = _get_ws_url("consulta")

    body = f"""<rConsDE xmlns="http://ekuatia.set.gov.py/sifen/xsd">
      <dCDC>{cdc}</dCDC>
    </rConsDE>"""

    envelope = _soap_envelope(body)
    headers = {
        "Content-Type": "application/soap+xml; charset=utf-8",
    }

    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.post(url, content=envelope.encode("utf-8"), headers=headers)
            resp.raise_for_status()
            resultado = _parse_respuesta_sifen(resp.text)
    except Exception as e:
        return {"codigo": "ERR", "mensaje": str(e), "protocolo": "", "raw": "", "estado": "error"}

    estado_map = {
        "0300": "aprobado",
        "0301": "rechazado",
        "0302": "cancelado",
    }
    resultado["estado"] = estado_map.get(resultado.get("codigo", ""), "desconocido")
    return resultado


def enviar_evento(
    tipo_evento: str,
    cdc: str,
    motivo: str,
    numero_evento: int = 1,
) -> dict:
    """
    Envía un evento SIFEN (cancelación, conformidad, etc.).
    
    tipo_evento: "gEvCan" (cancelación) | "gEvConf" | etc.
    
    Returns:
        dict con resultado del envío.
    """
    url = _get_ws_url("eventos")
    fe = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    body = f"""<rEnviEventoDE xmlns="http://ekuatia.set.gov.py/sifen/xsd">
      <dId>{uuid.uuid4()}</dId>
      <gGroupGtEve>
        <dFecFirma>{fe}</dFecFirma>
        <dVerFor>150</dVerFor>
        <gGroupTiEvt>
          <{tipo_evento}>
            <dCDCRef>{cdc}</dCDCRef>
            <dMotivo>{motivo}</dMotivo>
          </{tipo_evento}>
        </gGroupTiEvt>
      </gGroupGtEve>
    </rEnviEventoDE>"""

    envelope = _soap_envelope(body)
    headers = {
        "Content-Type": "application/soap+xml; charset=utf-8",
    }

    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.post(url, content=envelope.encode("utf-8"), headers=headers)
            resp.raise_for_status()
            resultado = _parse_respuesta_sifen(resp.text)
    except Exception as e:
        return {"codigo": "ERR", "mensaje": str(e), "protocolo": "", "raw": ""}

    resultado["aprobado"] = resultado.get("codigo") == "0300"
    return resultado


def enviar_inutilizacion(
    xml_inutilizacion: str,
) -> dict:
    """Envía solicitud de inutilización de rango de números al SIFEN."""
    url = _get_ws_url("inutilizacion")

    body = f"""<rEnviInu xmlns="http://ekuatia.set.gov.py/sifen/xsd">
      {xml_inutilizacion}
    </rEnviInu>"""

    envelope = _soap_envelope(body)
    headers = {
        "Content-Type": "application/soap+xml; charset=utf-8",
    }

    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.post(url, content=envelope.encode("utf-8"), headers=headers)
            resp.raise_for_status()
            return _parse_respuesta_sifen(resp.text)
    except Exception as e:
        return {"codigo": "ERR", "mensaje": str(e), "protocolo": "", "raw": ""}

def consultar_ruc_set(ruc: str, p12_path: str | None = None, p12_password: str | None = None) -> dict:
    """
    Consulta un RUC usando rConsRUC de SIFEN.
    Requiere certificado mTLS.
    Retorna la Razón Social y el Estado.
    """
    url = _get_ws_url("consulta") # La consulta de RUC suele ir al mismo endpoint de consultas generales
    
    body = f"""<rConsRUC xmlns="http://ekuatia.set.gov.py/sifen/xsd">
      <dId>{uuid.uuid4()}</dId>
      <dRUCCons>{ruc}</dRUCCons>
    </rConsRUC>"""

    envelope = _soap_envelope(body)
    headers = {"Content-Type": "application/soap+xml; charset=utf-8"}

    try:
        client_kwargs: dict = {"timeout": TIMEOUT, "verify": True}
        if p12_path and Path(p12_path).exists():
            try:
                import tempfile
                import os
                from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption
                p12_data = Path(p12_path).read_bytes()
                _pwd = p12_password.encode() if p12_password else None
                _key, _cert, _ = pkcs12.load_key_and_certificates(p12_data, _pwd)

                with tempfile.NamedTemporaryFile(suffix=".pem", delete=False) as cert_pem, \
                     tempfile.NamedTemporaryFile(suffix=".pem", delete=False) as key_pem:
                    cert_pem.write(_cert.public_bytes(Encoding.PEM))
                    key_pem.write(_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()))
                    cert_pem_path = cert_pem.name
                    key_pem_path = key_pem.name

                client_kwargs["cert"] = (cert_pem_path, key_pem_path)
                _temp_files = (cert_pem_path, key_pem_path)
            except Exception:
                _temp_files = ()
        else:
            _temp_files = ()

        with httpx.Client(**client_kwargs) as client:
            resp = client.post(url, content=envelope.encode("utf-8"), headers=headers)
            resp.raise_for_status()
            
            # Extraer razón social y estado
            root = etree.fromstring(resp.text.encode("utf-8"))
            ns = "http://ekuatia.set.gov.py/sifen/xsd"
            razon = root.find(f".//{{{ns}}}dRazCons")
            estado = root.find(f".//{{{ns}}}dDesEstCons")
            ruc_dv = root.find(f".//{{{ns}}}dDVCons")
            
            return {
                "ok": True,
                "razon_social": razon.text if razon is not None else "",
                "estado_ruc": estado.text if estado is not None else "",
                "dv": ruc_dv.text if ruc_dv is not None else "",
                "raw": resp.text
            }
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        import os as _os
        for _f in _temp_files:
            try:
                _os.unlink(_f)
            except Exception:
                pass
