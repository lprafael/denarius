"""
Firma Digital XMLDSig para Documentos Electrónicos, Eventos e Inutilizaciones SIFEN (Paraguay).

Cumple:
- Manual Técnico v150 SET/DNIT: firma RSA-SHA256 + XMLDSig enveloped.
- Certificado PKCS#12 (.p12) provisto por una PSC habilitada en Paraguay.
- DigestValue real (SHA-256) sobre nodo canónico C14N exclusivo.
"""
from __future__ import annotations

import base64
import hashlib
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import pkcs12
from lxml import etree


DSIG_NS = "http://www.w3.org/2000/09/xmldsig#"
C14N_EXC_ALG = "http://www.w3.org/2001/10/xml-exc-c14n#"
RSA_SHA256 = "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"
SHA256 = "http://www.w3.org/2001/04/xmlenc#sha256"


def _c14n(element: etree._Element) -> bytes:
    """Canonicalización C14N exclusiva (C14N 1.0) del elemento sin comentarios."""
    return etree.tostring(element, method="c14n", exclusive=True, with_comments=False)


def _sha256_b64(data: bytes) -> str:
    return base64.b64encode(hashlib.sha256(data).digest()).decode()


def _rsa_sha256_sign(private_key, data: bytes) -> str:
    signature = private_key.sign(data, padding.PKCS1v15(), hashes.SHA256())
    return base64.b64encode(signature).decode()


def _x509_b64(cert) -> str:
    der = cert.public_bytes(serialization.Encoding.DER)
    return base64.b64encode(der).decode()


def _construir_bloque_signature(
    target_id: str,
    target_c14n_bytes: bytes,
    private_key,
    cert,
) -> etree._Element:
    """Construye un elemento <ds:Signature> XMLDSig válido para el elemento referenciado."""
    dsig = f"{{{DSIG_NS}}}"
    digest_val = _sha256_b64(target_c14n_bytes)

    sig_el = etree.Element(f"{dsig}Signature", nsmap={"ds": DSIG_NS})

    signed_info = etree.SubElement(sig_el, f"{dsig}SignedInfo")

    canon_meth = etree.SubElement(signed_info, f"{dsig}CanonicalizationMethod")
    canon_meth.set("Algorithm", C14N_EXC_ALG)

    sig_meth = etree.SubElement(signed_info, f"{dsig}SignatureMethod")
    sig_meth.set("Algorithm", RSA_SHA256)

    reference = etree.SubElement(signed_info, f"{dsig}Reference")
    reference.set("URI", f"#{target_id}" if target_id else "")

    transforms = etree.SubElement(reference, f"{dsig}Transforms")
    tr1 = etree.SubElement(transforms, f"{dsig}Transform")
    tr1.set("Algorithm", "http://www.w3.org/2000/09/xmldsig#enveloped-signature")
    tr2 = etree.SubElement(transforms, f"{dsig}Transform")
    tr2.set("Algorithm", C14N_EXC_ALG)

    digest_meth = etree.SubElement(reference, f"{dsig}DigestMethod")
    digest_meth.set("Algorithm", SHA256)

    dv_el = etree.SubElement(reference, f"{dsig}DigestValue")
    dv_el.text = digest_val

    # Firmar SignedInfo canonicalizado
    signed_info_c14n = _c14n(signed_info)
    signature_val = _rsa_sha256_sign(private_key, signed_info_c14n)

    sv_el = etree.SubElement(sig_el, f"{dsig}SignatureValue")
    sv_el.text = signature_val

    # KeyInfo
    key_info = etree.SubElement(sig_el, f"{dsig}KeyInfo")
    x509_data = etree.SubElement(key_info, f"{dsig}X509Data")
    x509_cert = etree.SubElement(x509_data, f"{dsig}X509Certificate")
    x509_cert.text = _x509_b64(cert)

    return sig_el


def firmar_xml_rde(xml_str: str, p12_path: str, p12_password: str) -> str:
    """
    Firma digitalmente el XML rDE con el certificado PKCS#12 (.p12).
    Calcula el DigestValue sobre el nodo <DE Id="CDC"> y ubica la firma antes de <gCamFuFD>.
    """
    p12_data = Path(p12_path).read_bytes()
    private_key, cert, _ = pkcs12.load_key_and_certificates(
        p12_data, p12_password.encode() if p12_password else None
    )

    root = etree.fromstring(xml_str.encode("utf-8"))
    ns = {"s": root.nsmap.get(None, "http://ekuatia.set.gov.py/sifen/xsd")}

    de_node = root.find(f'{{{ns["s"]}}}DE')
    if de_node is None:
        raise ValueError("No se encontró el nodo DE en el XML")

    cdc = de_node.get("Id", "")
    de_c14n = _c14n(de_node)

    sig_el = _construir_bloque_signature(cdc, de_c14n, private_key, cert)

    # Eliminar placeholders
    dsig = f"{{{DSIG_NS}}}"
    for old_sig in root.findall(f"{dsig}Signature"):
        root.remove(old_sig)

    # Insertar antes de gCamFuFD (QR)
    sifen_ns = ns["s"]
    qr_node = root.find(f'{{{sifen_ns}}}gCamFuFD')
    if qr_node is not None:
        qr_idx = list(root).index(qr_node)
        root.insert(qr_idx, sig_el)
    else:
        root.append(sig_el)

    xml_bytes = etree.tostring(root, encoding="utf-8", xml_declaration=True, pretty_print=False)
    return xml_bytes.decode("utf-8")


def firmar_xml_evento(xml_evento_str: str, p12_path: str, p12_password: str, id_evento: str = "") -> str:
    """
    Firma digitalmente un mensaje de eventos SIFEN (<rEnviEventoDe>) sobre el nodo <gGroupGtEve>.
    """
    p12_data = Path(p12_path).read_bytes()
    private_key, cert, _ = pkcs12.load_key_and_certificates(
        p12_data, p12_password.encode() if p12_password else None
    )

    root = etree.fromstring(xml_evento_str.encode("utf-8"))
    ns = {"s": root.nsmap.get(None, "http://ekuatia.set.gov.py/sifen/xsd")}

    evt_node = root.find(f'.//{{{ns["s"]}}}gGroupGtEve')
    if evt_node is None:
        evt_node = root  # Fallback a root si es elemento directo

    evt_c14n = _c14n(evt_node)
    sig_el = _construir_bloque_signature(id_evento, evt_c14n, private_key, cert)

    root.append(sig_el)
    xml_bytes = etree.tostring(root, encoding="utf-8", xml_declaration=True, pretty_print=False)
    return xml_bytes.decode("utf-8")


def firmar_xml_inutilizacion(xml_inu_str: str, p12_path: str, p12_password: str, id_inut: str = "") -> str:
    """
    Firma digitalmente una solicitud de inutilización de numeración (<rEnviInu> / <rGeLiInut>).
    """
    p12_data = Path(p12_path).read_bytes()
    private_key, cert, _ = pkcs12.load_key_and_certificates(
        p12_data, p12_password.encode() if p12_password else None
    )

    root = etree.fromstring(xml_inu_str.encode("utf-8"))
    ns = {"s": root.nsmap.get(None, "http://ekuatia.set.gov.py/sifen/xsd")}

    inu_node = root.find(f'.//{{{ns["s"]}}}dInut')
    if inu_node is None:
        inu_node = root
    inu_c14n = _c14n(inu_node)
    sig_el = _construir_bloque_signature(id_inut, inu_c14n, private_key, cert)

    root.append(sig_el)
    xml_bytes = etree.tostring(root, encoding="utf-8", xml_declaration=True, pretty_print=False)
    return xml_bytes.decode("utf-8")


def extraer_digest_value(xml_firmado_str: str) -> str:
    """Extrae el DigestValue en Base64 del XML firmado."""
    root = etree.fromstring(xml_firmado_str.encode("utf-8"))
    dsig = f"{{{DSIG_NS}}}"
    dv = root.find(f".//{dsig}DigestValue")
    if dv is not None and dv.text:
        return dv.text.strip()
    return ""
