"""
Cliente SIFEN Oficial — Webservices DNIT / SET Paraguay (Manual Técnico v150 y Guía Octubre 2024).

Implementa:
- Envío Asíncrono de Lotes DE (rEnvioLote / rLoteDE comprimido en ZIP Base64) -> recibe-lote.wsdl.
- Consulta de Lote por Protocolo (rEnviConsLoteDe) -> consulta-lote.wsdl.
- Consulta de DE por CDC (rEnviConsDeRequest) -> consulta.wsdl.
- Consulta de RUC (rConsRUC) -> consulta-ruc.wsdl.
- Envío de Eventos Firmados (rEnviEventoDe) -> evento.wsdl.
- Envío de Inutilización Firmada (rEnviInu) -> inutiliza.wsdl.
- Recepción Síncrona Unitaria (rEnviDe) -> recibe.wsdl.

Autenticación mutua TLS 1.2 (mTLS) con certificados PKCS#12 (.p12) emitidos por PSC habilitadas.
"""
from __future__ import annotations

import base64
import io
import os
import tempfile
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import requests
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    pkcs12,
)
from lxml import etree

from app.config import settings

TIMEOUT = 60  # segundos
SIFEN_NS = "http://ekuatia.set.gov.py/sifen/xsd"


def _get_ws_url(servicio: str) -> str:
    """Retorna URL del WS según ambiente configurado (test o prod)."""
    amb = settings.sifen_ambiente.lower()
    mapa = {
        "async_lote": settings.sifen_ws_async_lote_test if amb == "test" else settings.sifen_ws_async_lote_prod,
        "cons_lote": settings.sifen_ws_cons_lote_test if amb == "test" else settings.sifen_ws_cons_lote_prod,
        "consulta_cdc": settings.sifen_ws_consulta_test if amb == "test" else settings.sifen_ws_consulta_prod,
        "consulta_ruc": settings.sifen_ws_consulta_ruc_test if amb == "test" else settings.sifen_ws_consulta_ruc_prod,
        "eventos": settings.sifen_ws_eventos_test if amb == "test" else settings.sifen_ws_eventos_prod,
        "inutilizacion": settings.sifen_ws_inutilizacion_test if amb == "test" else settings.sifen_ws_inutilizacion_prod,
        "recepcion_sync": settings.sifen_ws_url_test if amb == "test" else settings.sifen_ws_url_prod,
    }
    return mapa.get(servicio, settings.sifen_ws_url_test)


def _soap_envelope(body_content: str) -> str:
    """Construye un envelope SOAP 1.2 estandarizado."""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope"
               xmlns:xsd="{SIFEN_NS}">
  <soap:Header/>
  <soap:Body>
    {body_content}
  </soap:Body>
</soap:Envelope>"""


def _extraer_cert_mtls(p12_path: str | None, p12_password: str | None = None) -> tuple[tuple[str, str] | None, list[str]]:
    """Extrae certificados PEM temporales para autenticación mTLS con requests."""
    temp_files = []
    cert_tuple = None

    if p12_path and Path(p12_path).exists():
        try:
            p12_data = Path(p12_path).read_bytes()
            _pwd = p12_password.encode() if p12_password else None
            _key, _cert, _ = pkcs12.load_key_and_certificates(p12_data, _pwd)

            with tempfile.NamedTemporaryFile(suffix=".pem", delete=False) as cert_pem, \
                 tempfile.NamedTemporaryFile(suffix=".pem", delete=False) as key_pem:
                cert_pem.write(_cert.public_bytes(Encoding.PEM))
                key_pem.write(_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()))
                cert_path = cert_pem.name
                key_path = key_pem.name

            temp_files.extend([cert_path, key_path])
            cert_tuple = (cert_path, key_path)
        except Exception as e:
            print(f"[mTLS] Error al cargar certificado .p12: {e}")

    return cert_tuple, temp_files


def _limpiar_temp_files(files: list[str]) -> None:
    for f in files:
        try:
            if os.path.exists(f):
                os.unlink(f)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# 1. Envío Asíncrono de Lotes (recibe-lote.wsdl)
# ---------------------------------------------------------------------------
def enviar_lote_asincrono(
    lista_xml_firmados: list[str],
    d_id: str | None = None,
    p12_path: str | None = None,
    p12_password: str | None = None,
) -> dict:
    """
    Empaqueta hasta 50 DEs firmados en un lote comprimido en ZIP Base64 y lo envía al WS asíncrono.
    """
    if not lista_xml_firmados:
        raise ValueError("El lote debe contener al menos un Documento Electrónico")
    if len(lista_xml_firmados) > 50:
        raise ValueError("El lote no puede exceder los 50 Documentos Electrónicos")

    d_id = d_id or datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

    r_lote_parts = ['<?xml version="1.0" encoding="UTF-8"?><rLoteDE xmlns="http://ekuatia.set.gov.py/sifen/xsd">']
    for de_xml in lista_xml_firmados:
        xml_clean = de_xml.strip()
        if xml_clean.startswith("<?xml"):
            xml_clean = xml_clean.split("?>", 1)[1].strip()
        r_lote_parts.append(xml_clean)
    r_lote_parts.append("</rLoteDE>")
    r_lote_xml_str = "".join(r_lote_parts)

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("lote.xml", r_lote_xml_str.encode("utf-8"))
    zip_bytes = zip_buffer.getvalue()

    if len(zip_bytes) > 1024 * 1000:
        raise ValueError(f"El archivo ZIP del lote supera el límite permitido de 1000 KB ({len(zip_bytes)/1024:.1f} KB)")

    zip_b64 = base64.b64encode(zip_bytes).decode("ascii")

    body = f"""<xsd:rEnvioLote>
      <xsd:dId>{d_id}</xsd:dId>
      <xsd:xDE>{zip_b64}</xsd:xDE>
    </xsd:rEnvioLote>"""

    envelope = _soap_envelope(body)
    headers = {"Content-Type": "application/soap+xml; charset=utf-8"}
    url = _get_ws_url("async_lote")

    cert_tuple, temp_files = _extraer_cert_mtls(p12_path, p12_password)
    try:
        resp = requests.post(url, data=envelope.encode("utf-8"), headers=headers, cert=cert_tuple, timeout=TIMEOUT)
        resp.raise_for_status()
        raw_text = resp.text

        root = etree.fromstring(raw_text.encode("utf-8"))
        cod_res = root.find(f".//{{{SIFEN_NS}}}dCodRes")
        msg_res = root.find(f".//{{{SIFEN_NS}}}dMsgRes")
        prot_cons = root.find(f".//{{{SIFEN_NS}}}dProtConsLote")
        tpo_proc = root.find(f".//{{{SIFEN_NS}}}dTpoProces")

        c_res = cod_res.text.strip() if cod_res is not None and cod_res.text else ""
        m_res = msg_res.text.strip() if msg_res is not None and msg_res.text else ""
        p_cons = prot_cons.text.strip() if prot_cons is not None and prot_cons.text else ""
        t_proc = tpo_proc.text.strip() if tpo_proc is not None and tpo_proc.text else "0"

        return {
            "ok": True,
            "d_id": d_id,
            "codigo": c_res,
            "mensaje": m_res,
            "protocolo_lote": p_cons,
            "tiempo_proceso": t_proc,
            "encolado": c_res == "0300",
            "raw": raw_text,
            "zip_b64": zip_b64,
        }
    except Exception as e:
        return {
            "ok": False,
            "d_id": d_id,
            "codigo": "ERR",
            "mensaje": str(e),
            "protocolo_lote": "",
            "encolado": False,
            "raw": "",
            "zip_b64": zip_b64,
        }
    finally:
        _limpiar_temp_files(temp_files)


# ---------------------------------------------------------------------------
# 2. Consulta de Lote por Protocolo (consulta-lote.wsdl)
# ---------------------------------------------------------------------------
def consultar_lote(
    d_prot_cons_lote: str,
    d_id: str | None = None,
    p12_path: str | None = None,
    p12_password: str | None = None,
) -> dict:
    """Consulta el resultado de procesamiento de un lote mediante su número de protocolo."""
    d_id = d_id or "1"
    url = _get_ws_url("cons_lote")

    body = f"""<xsd:rEnviConsLoteDe>
      <xsd:dId>{d_id}</xsd:dId>
      <xsd:dProtConsLote>{d_prot_cons_lote}</xsd:dProtConsLote>
    </xsd:rEnviConsLoteDe>"""

    envelope = _soap_envelope(body)
    headers = {"Content-Type": "application/soap+xml; charset=utf-8"}

    cert_tuple, temp_files = _extraer_cert_mtls(p12_path, p12_password)
    try:
        resp = requests.post(url, data=envelope.encode("utf-8"), headers=headers, cert=cert_tuple, timeout=TIMEOUT)
        resp.raise_for_status()
        raw_text = resp.text

        root = etree.fromstring(raw_text.encode("utf-8"))
        cod_lot = root.find(f".//{{{SIFEN_NS}}}dCodResLot")
        msg_lot = root.find(f".//{{{SIFEN_NS}}}dMsgResLot")

        c_lot = cod_lot.text.strip() if cod_lot is not None and cod_lot.text else ""
        m_lot = msg_lot.text.strip() if msg_lot is not None and msg_lot.text else ""

        documentos_procesados = []
        for g_res in root.findall(f".//{{{SIFEN_NS}}}gResProcLote"):
            cdc_el = g_res.find(f"{{{SIFEN_NS}}}id")
            est_el = g_res.find(f"{{{SIFEN_NS}}}dEstRes")
            prot_el = g_res.find(f"{{{SIFEN_NS}}}dProtAut")
            
            c_doc = ""
            m_doc = ""
            g_proc = g_res.find(f"{{{SIFEN_NS}}}gResProc")
            if g_proc is not None:
                c_proc = g_proc.find(f"{{{SIFEN_NS}}}dCodRes")
                m_proc = g_proc.find(f"{{{SIFEN_NS}}}dMsgRes")
                c_doc = c_proc.text.strip() if c_proc is not None and c_proc.text else ""
                m_doc = m_proc.text.strip() if m_proc is not None and m_proc.text else ""

            documentos_procesados.append({
                "cdc": cdc_el.text.strip() if cdc_el is not None and cdc_el.text else "",
                "estado": est_el.text.strip() if est_el is not None and est_el.text else "",
                "protocolo_autorizacion": prot_el.text.strip() if prot_el is not None and prot_el.text else "",
                "codigo_resultado": c_doc,
                "mensaje_resultado": m_doc,
            })

        return {
            "ok": True,
            "codigo_lote": c_lot,
            "mensaje_lote": m_lot,
            "estado_lote": "concluido" if c_lot == "0362" else ("en_proceso" if c_lot == "0361" else "error"),
            "documentos": documentos_procesados,
            "raw": raw_text,
        }
    except Exception as e:
        return {
            "ok": False,
            "codigo_lote": "ERR",
            "mensaje_lote": str(e),
            "estado_lote": "error",
            "documentos": [],
            "raw": "",
        }
    finally:
        _limpiar_temp_files(temp_files)


# ---------------------------------------------------------------------------
# 3. Consulta de Documento por CDC (consulta.wsdl)
# ---------------------------------------------------------------------------
def consultar_de_por_cdc(
    cdc: str,
    d_id: str | None = None,
    p12_path: str | None = None,
    p12_password: str | None = None,
) -> dict:
    """Consulta un Documento Electrónico por su CDC."""
    d_id = d_id or "1"
    url = _get_ws_url("consulta_cdc")

    body = f"""<xsd:rEnviConsDeRequest>
      <xsd:dId>{d_id}</xsd:dId>
      <xsd:dCDC>{cdc.strip()}</xsd:dCDC>
    </xsd:rEnviConsDeRequest>"""

    envelope = _soap_envelope(body)
    headers = {"Content-Type": "application/soap+xml; charset=utf-8"}

    cert_tuple, temp_files = _extraer_cert_mtls(p12_path, p12_password)
    try:
        resp = requests.post(url, data=envelope.encode("utf-8"), headers=headers, cert=cert_tuple, timeout=TIMEOUT)
        resp.raise_for_status()
        raw_text = resp.text

        root = etree.fromstring(raw_text.encode("utf-8"))
        cod_res = root.find(f".//{{{SIFEN_NS}}}dCodRes")
        msg_res = root.find(f".//{{{SIFEN_NS}}}dMsgRes")
        x_conten = root.find(f".//{{{SIFEN_NS}}}xContenDE")

        c_res = cod_res.text.strip() if cod_res is not None and cod_res.text else ""
        m_res = msg_res.text.strip() if msg_res is not None and msg_res.text else ""
        xml_de = x_conten.text.strip() if x_conten is not None and x_conten.text else ""

        return {
            "ok": True,
            "codigo": c_res,
            "mensaje": m_res,
            "aprobado": c_res == "0422",
            "xml_de": xml_de,
            "raw": raw_text,
        }
    except Exception as e:
        return {
            "ok": False,
            "codigo": "ERR",
            "mensaje": str(e),
            "aprobado": False,
            "xml_de": "",
            "raw": "",
        }
    finally:
        _limpiar_temp_files(temp_files)


# ---------------------------------------------------------------------------
# 4. Consulta de RUC (consulta-ruc.wsdl)
# ---------------------------------------------------------------------------
def consultar_ruc_set(
    ruc: str,
    d_id: str | None = None,
    p12_path: str | None = None,
    p12_password: str | None = None,
) -> dict:
    """Consulta estado y razón social de un RUC ante la DNIT / SIFEN."""
    d_id = d_id or str(uuid.uuid4())
    url = _get_ws_url("consulta_ruc")

    body = f"""<xsd:rConsRUC>
      <xsd:dId>{d_id}</xsd:dId>
      <xsd:dRUCCons>{ruc.strip()}</xsd:dRUCCons>
    </xsd:rConsRUC>"""

    envelope = _soap_envelope(body)
    headers = {"Content-Type": "application/soap+xml; charset=utf-8"}

    cert_tuple, temp_files = _extraer_cert_mtls(p12_path, p12_password)
    try:
        resp = requests.post(url, data=envelope.encode("utf-8"), headers=headers, cert=cert_tuple, timeout=TIMEOUT)
        resp.raise_for_status()
        raw_text = resp.text

        root = etree.fromstring(raw_text.encode("utf-8"))
        razon = root.find(f".//{{{SIFEN_NS}}}dRazCons")
        estado = root.find(f".//{{{SIFEN_NS}}}dDesEstCons")
        ruc_dv = root.find(f".//{{{SIFEN_NS}}}dDVCons")
        cod_res = root.find(f".//{{{SIFEN_NS}}}dCodRes")

        return {
            "ok": True,
            "codigo": cod_res.text.strip() if cod_res is not None and cod_res.text else "0500",
            "razon_social": razon.text.strip() if razon is not None and razon.text else "",
            "estado_ruc": estado.text.strip() if estado is not None and estado.text else "ACTIVO",
            "dv": ruc_dv.text.strip() if ruc_dv is not None and ruc_dv.text else "",
            "raw": raw_text,
        }
    except Exception as e:
        return {"ok": False, "codigo": "ERR", "error": str(e), "razon_social": "", "estado_ruc": "", "dv": ""}
    finally:
        _limpiar_temp_files(temp_files)


# ---------------------------------------------------------------------------
# 5. Envío de Eventos Firmados (evento.wsdl)
# ---------------------------------------------------------------------------
def enviar_evento_firmado(
    tipo_evento: str,
    cdc: str,
    motivo: str,
    p12_path: str | None = None,
    p12_password: str | None = None,
) -> dict:
    """Construye, firma con XMLDSig y envía un evento oficial al WS SIFEN."""
    from app.sifen.firma import firmar_xml_evento

    url = _get_ws_url("eventos")
    fe = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    evt_id = f"EVT-{cdc[-10:]}-{datetime.now().strftime('%H%M%S')}"

    xml_evt_base = f"""<rEnviEventoDe xmlns="http://ekuatia.set.gov.py/sifen/xsd">
  <dId>{uuid.uuid4()}</dId>
  <dFecFirma>{fe}</dFecFirma>
  <dVerFor>150</dVerFor>
  <gGroupGtEve Id="{evt_id}">
    <gGroupTiEvt>
      <{tipo_evento}>
        <dCDCRef>{cdc.strip()}</dCDCRef>
        <dMotivo>{motivo.strip()}</dMotivo>
      </{tipo_evento}>
    </gGroupTiEvt>
  </gGroupGtEve>
</rEnviEventoDe>"""

    if p12_path and Path(p12_path).exists():
        try:
            xml_firmado = firmar_xml_evento(xml_evt_base, p12_path, p12_password or "", evt_id)
        except Exception:
            xml_firmado = xml_evt_base
    else:
        xml_firmado = xml_evt_base

    envelope = _soap_envelope(xml_firmado)
    headers = {"Content-Type": "application/soap+xml; charset=utf-8"}

    cert_tuple, temp_files = _extraer_cert_mtls(p12_path, p12_password)
    try:
        resp = requests.post(url, data=envelope.encode("utf-8"), headers=headers, cert=cert_tuple, timeout=TIMEOUT)
        resp.raise_for_status()
        raw_text = resp.text

        root = etree.fromstring(raw_text.encode("utf-8"))
        cod_res = root.find(f".//{{{SIFEN_NS}}}dCodRes")
        msg_res = root.find(f".//{{{SIFEN_NS}}}dMsgRes")

        c_res = cod_res.text.strip() if cod_res is not None and cod_res.text else ""
        m_res = msg_res.text.strip() if msg_res is not None and msg_res.text else ""

        return {
            "ok": True,
            "codigo": c_res,
            "mensaje": m_res,
            "aprobado": c_res in ("0600", "0300"),
            "raw": raw_text,
            "xml_evento": xml_firmado,
        }
    except Exception as e:
        return {
            "ok": False,
            "codigo": "ERR",
            "mensaje": str(e),
            "aprobado": False,
            "raw": "",
            "xml_evento": xml_firmado,
        }
    finally:
        _limpiar_temp_files(temp_files)


# ---------------------------------------------------------------------------
# 6. Envío de Inutilización Firmada (inutiliza.wsdl)
# ---------------------------------------------------------------------------
def enviar_inutilizacion_firmada(
    num_timbrado: str,
    d_est: str,
    d_pun_exp: str,
    d_num_ini: int,
    d_num_fin: int,
    i_ti_de: int,
    motivo: str,
    ruc_emisor: str,
    dv_emisor: str,
    p12_path: str | None = None,
    p12_password: str | None = None,
) -> dict:
    """Construye, firma y envía una solicitud de inutilización de numeración."""
    from app.sifen.firma import firmar_xml_inutilizacion

    url = _get_ws_url("inutilizacion")
    fe = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    inut_id = f"INU-{d_est}{d_pun_exp}-{d_num_ini}-{d_num_fin}"

    xml_inu_base = f"""<rEnviInu xmlns="http://ekuatia.set.gov.py/sifen/xsd">
  <dId>{uuid.uuid4()}</dId>
  <dFecFirma>{fe}</dFecFirma>
  <dVerFor>150</dVerFor>
  <dInut Id="{inut_id}">
    <dNumTim>{num_timbrado.strip()}</dNumTim>
    <dEst>{str(d_est).zfill(3)}</dEst>
    <dPunExp>{str(d_pun_exp).zfill(3)}</dPunExp>
    <dNumIni>{d_num_ini}</dNumIni>
    <dNumFin>{d_num_fin}</dNumFin>
    <iTiDE>{i_ti_de}</iTiDE>
    <dMotInu>{motivo.strip()}</dMotInu>
    <dRucEm>{ruc_emisor.strip().zfill(8)}</dRucEm>
    <dDVEmi>{dv_emisor.strip()}</dDVEmi>
  </dInut>
</rEnviInu>"""

    if p12_path and Path(p12_path).exists():
        try:
            xml_firmado = firmar_xml_inutilizacion(xml_inu_base, p12_path, p12_password or "", inut_id)
        except Exception:
            xml_firmado = xml_inu_base
    else:
        xml_firmado = xml_inu_base

    envelope = _soap_envelope(xml_firmado)
    headers = {"Content-Type": "application/soap+xml; charset=utf-8"}

    cert_tuple, temp_files = _extraer_cert_mtls(p12_path, p12_password)
    try:
        resp = requests.post(url, data=envelope.encode("utf-8"), headers=headers, cert=cert_tuple, timeout=TIMEOUT)
        resp.raise_for_status()
        raw_text = resp.text

        root = etree.fromstring(raw_text.encode("utf-8"))
        cod_res = root.find(f".//{{{SIFEN_NS}}}dCodRes")
        msg_res = root.find(f".//{{{SIFEN_NS}}}dMsgRes")

        c_res = cod_res.text.strip() if cod_res is not None and cod_res.text else ""
        m_res = msg_res.text.strip() if msg_res is not None and msg_res.text else ""

        return {
            "ok": True,
            "codigo": c_res,
            "mensaje": m_res,
            "aprobado": c_res in ("0700", "0300"),
            "raw": raw_text,
            "xml_inutilizacion": xml_firmado,
        }
    except Exception as e:
        return {
            "ok": False,
            "codigo": "ERR",
            "mensaje": str(e),
            "aprobado": False,
            "raw": "",
            "xml_inutilizacion": xml_firmado,
        }
    finally:
        _limpiar_temp_files(temp_files)


# ---------------------------------------------------------------------------
# 7. Envío Síncrono Unitario (recibe.wsdl)
# ---------------------------------------------------------------------------
def enviar_lote_de(
    xml_firmado: str,
    cdc: str,
    p12_path: str | None = None,
    p12_password: str | None = None,
) -> dict:
    """Envía un Documento Electrónico individual al WS síncrono de SIFEN."""
    url = _get_ws_url("recepcion_sync")

    body = f"""<rEnviDe xmlns="{SIFEN_NS}">
      <dId>{datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")}</dId>
      <xDE>{xml_firmado.strip()}</xDE>
    </rEnviDe>"""

    envelope = _soap_envelope(body)
    headers = {"Content-Type": "application/soap+xml; charset=utf-8"}

    cert_tuple, temp_files = _extraer_cert_mtls(p12_path, p12_password)
    try:
        resp = requests.post(url, data=envelope.encode("utf-8"), headers=headers, cert=cert_tuple, timeout=TIMEOUT)
        resp.raise_for_status()
        raw_text = resp.text

        root = etree.fromstring(raw_text.encode("utf-8"))
        cod_res = root.find(f".//{{{SIFEN_NS}}}dCodRes")
        msg_res = root.find(f".//{{{SIFEN_NS}}}dMsgRes")
        prot = root.find(f".//{{{SIFEN_NS}}}dProtAut")

        c_res = cod_res.text.strip() if cod_res is not None and cod_res.text else ""
        m_res = msg_res.text.strip() if msg_res is not None and msg_res.text else ""
        p_res = prot.text.strip() if prot is not None and prot.text else ""

        return {
            "ok": True,
            "codigo": c_res,
            "mensaje": m_res,
            "protocolo": p_res,
            "aprobado": c_res == "0300",
            "raw": raw_text,
        }
    except Exception as e:
        return {
            "ok": False,
            "codigo": "ERR",
            "mensaje": str(e),
            "protocolo": "",
            "aprobado": False,
            "raw": "",
        }
    finally:
        _limpiar_temp_files(temp_files)
