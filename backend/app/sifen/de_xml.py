from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models import Emisor, Factura, FacturaLinea

from app.config import settings
from app.sifen.totales import LineaIVADetail, TotalesDE

NS = settings.sifen_xmlns
XSI = "http://www.w3.org/2001/XMLSchema-instance"
DSIG = "http://www.w3.org/2000/09/xmldsig#"

TIPO_DOC_DESC = {
    1: "Factura electrónica",
    2: "Factura electrónica de exportación",
    3: "Factura electrónica de importación",
    4: "Autofactura electrónica",
    5: "Nota de crédito electrónica",
    6: "Nota de débito electrónica",
    7: "Nota de remisión electrónica",
}

MOTIVO_NC_DESC = {
    1: "Devolución",
    2: "Descuento",
    3: "Bonificación",
    4: "Crédito incobrable",
    5: "Recupero de costo",
    6: "Recupero de gasto",
    7: "Anulación",
}

MONEDAS_DESC = {
    "PYG": "Guarani",
    "USD": "Dolar Americano",
    "BRL": "Real",
    "ARS": "Peso Argentino",
    "EUR": "Euro",
}


def _el(parent: ET.Element, tag: str, text: str | int | float | None = None) -> ET.Element:
    e = ET.SubElement(parent, f"{{{NS}}}{tag}")
    if text is not None:
        val = str(text).strip()
        e.text = val
    return e


def _sub_text(parent: ET.Element, tag: str, value: str | int | float | None) -> None:
    """Inserta tag solo si tiene un valor no vacío (cumple regla SIFEN de omisión de tags vacíos)."""
    if value is not None:
        val = str(value).strip()
        if val != "":
            _el(parent, tag, val)


def construir_xml_rde(
    *,
    emisor: "Emisor",
    factura: "Factura",
    lineas: list["FacturaLinea"],
    detalles_iva: list[LineaIVADetail],
    tot: TotalesDE,
    incluir_transporte_ejemplo: bool = False,
) -> str:
    """
    Construye el XML rDE oficial conforme a la especificación técnica v150 de SIFEN / e-Kuatia.
    Soporta Facturas (1), Exportación (2), Autofacturas (4), Notas de Crédito (5), Notas de Débito (6) y Remisiones (7).
    """
    cdc = factura.cdc.strip()
    fe_emi = factura.d_fe_emi_de
    if isinstance(fe_emi, datetime):
        d_fe_emi_str = fe_emi.strftime("%Y-%m-%dT%H:%M:%S")
    else:
        d_fe_emi_str = str(fe_emi).strip()

    rde = ET.Element(f"{{{NS}}}rDE")
    rde.set(f"{{{XSI}}}schemaLocation", "https://ekuatia.set.gov.py/sifen/xsd siRecepDE_v150.xsd")

    _sub_text(rde, "dVerFor", settings.d_ver_for)

    # ---------------------------------------------------------------------------
    # DE (Documento Electrónico)
    # ---------------------------------------------------------------------------
    de = ET.SubElement(rde, f"{{{NS}}}DE")
    de.set("Id", cdc)

    _sub_text(de, "dDVId", cdc[-1])
    _sub_text(de, "dFecFirma", d_fe_emi_str[:19])
    _sub_text(de, "dSisFact", 1)

    # ---------------------------------------------------------------------------
    # gOpeDE
    # ---------------------------------------------------------------------------
    g_ope = _el(de, "gOpeDE")
    _sub_text(g_ope, "iTipEmi", factura.i_tip_emi)
    _sub_text(g_ope, "dDesTipEmi", "Normal" if factura.i_tip_emi == 1 else "Contingencia")
    _sub_text(g_ope, "dCodSeg", str(factura.d_cod_seg).zfill(9))
    _sub_text(g_ope, "dInfoEmi", 1)
    _sub_text(g_ope, "dInfoFisc", "Información de interés del Fisco respecto al DE")

    # ---------------------------------------------------------------------------
    # gTimb
    # ---------------------------------------------------------------------------
    g_timb = _el(de, "gTimb")
    i_ti_de = factura.i_ti_de
    _sub_text(g_timb, "iTiDE", i_ti_de)
    _sub_text(g_timb, "dDesTiDE", TIPO_DOC_DESC.get(i_ti_de, "Factura electrónica"))
    _sub_text(g_timb, "dNumTim", str(emisor.num_tim).strip())
    _sub_text(g_timb, "dEst", str(emisor.d_est).zfill(3))
    _sub_text(g_timb, "dPunExp", str(emisor.d_pun_exp).zfill(3))
    _sub_text(g_timb, "dNumDoc", str(factura.numero_documento).zfill(7))
    if getattr(emisor, "d_serie_num", None):
        _sub_text(g_timb, "dSerieNum", emisor.d_serie_num.strip())
    _sub_text(g_timb, "dFeIniT", str(emisor.d_fe_ini_t).strip())

    # ---------------------------------------------------------------------------
    # gDatGralOpe
    # ---------------------------------------------------------------------------
    g_dat = _el(de, "gDatGralOpe")
    _sub_text(g_dat, "dFeEmiDE", d_fe_emi_str)

    # gOpeCom
    moneda = getattr(factura, "moneda", "PYG") or "PYG"
    tipo_cambio = getattr(factura, "tipo_cambio", 1.0) or 1.0
    cond_tipo_cambio = getattr(factura, "condicion_tipo_cambio", 1) or 1

    g_ope_com = _el(g_dat, "gOpeCom")
    _sub_text(g_ope_com, "iTipTra", 1 if i_ti_de != 2 else 2)
    _sub_text(g_ope_com, "dDesTipTra", "Venta de mercadería" if i_ti_de != 2 else "Exportación")
    _sub_text(g_ope_com, "iTImp", 1)
    _sub_text(g_ope_com, "dDesTImp", "IVA")
    _sub_text(g_ope_com, "cMoneOpe", moneda)
    _sub_text(g_ope_com, "dDesMoneOpe", MONEDAS_DESC.get(moneda, "Guarani"))
    if moneda != "PYG":
        _sub_text(g_ope_com, "dCondTiCam", cond_tipo_cambio)
        _sub_text(g_ope_com, "dTiCam", int(round(tipo_cambio)) if tipo_cambio.is_integer() else tipo_cambio)

    # gEmis
    g_emis = _el(g_dat, "gEmis")
    ruc_clean = emisor.ruc_con_dv.replace(" ", "").strip()
    ruc_parts = ruc_clean.split("-") if "-" in ruc_clean else [ruc_clean, "0"]
    _sub_text(g_emis, "dRucEm", ruc_parts[0].zfill(8))
    _sub_text(g_emis, "dDVEmi", ruc_parts[1] if len(ruc_parts) > 1 else "0")
    _sub_text(g_emis, "iTipCont", emisor.tipo_contribuyente)
    _sub_text(g_emis, "cTipReg", emisor.c_tip_reg)
    _sub_text(g_emis, "dNomEmi", emisor.razon_social.strip())
    if getattr(emisor, "nombre_fantasia", None):
        _sub_text(g_emis, "dNomFan", emisor.nombre_fantasia.strip())
    _sub_text(g_emis, "dDirEmi", emisor.direccion.strip())
    _sub_text(g_emis, "dNumCas", str(emisor.num_casa).strip() or "0")
    _sub_text(g_emis, "cDepEmi", int(emisor.c_dep_emi))
    _sub_text(g_emis, "dDesDepEmi", emisor.d_des_dep_emi.strip())
    _sub_text(g_emis, "cCiuEmi", int(emisor.c_ciu_emi))
    _sub_text(g_emis, "dDesCiuEmi", emisor.d_des_ciu_emi.strip())
    _sub_text(g_emis, "dTelEmi", emisor.telefono.strip())
    _sub_text(g_emis, "dEmailE", emisor.email.strip())

    g_act = _el(g_emis, "gActEco")
    _sub_text(g_act, "cActEco", emisor.c_act_eco.strip())
    _sub_text(g_act, "dDesActEco", emisor.d_des_act_eco.strip())

    # gDatRec
    g_rec = _el(g_dat, "gDatRec")
    rec_ruc_raw = factura.receptor_ruc.replace(" ", "").strip()
    es_contribuyente = bool(rec_ruc_raw and rec_ruc_raw != "44444401" and factura.receptor_dv)

    _sub_text(g_rec, "iNatRec", 1 if es_contribuyente else 2)
    _sub_text(g_rec, "iTiOpe", 1 if es_contribuyente else 2)
    _sub_text(g_rec, "cPaisRec", "PRY")
    _sub_text(g_rec, "dDesPaisRe", "Paraguay")
    _sub_text(g_rec, "iTiContRec", 2 if es_contribuyente else 1)

    if es_contribuyente:
        _sub_text(g_rec, "dRucRec", rec_ruc_raw.zfill(8))
        _sub_text(g_rec, "dDVRec", factura.receptor_dv.strip())
    else:
        _sub_text(g_rec, "iTipIDRec", 1)  # Cédula paraguaya
        _sub_text(g_rec, "dNumIDRec", rec_ruc_raw or "0")

    _sub_text(g_rec, "dNomRec", factura.receptor_nombre.strip())
    if getattr(factura, "receptor_dir", None):
        _sub_text(g_rec, "dDirRec", factura.receptor_dir.strip())
    _sub_text(g_rec, "dNumCasRec", str(getattr(factura, "receptor_num_cas", "0")).strip() or "0")
    _sub_text(g_rec, "cDepRec", int(factura.c_dep_rec))
    _sub_text(g_rec, "dDesDepRec", factura.d_des_dep_rec.strip())
    _sub_text(g_rec, "cDisRec", int(factura.c_dis_rec))
    _sub_text(g_rec, "dDesDisRec", factura.d_des_dis_rec.strip())
    _sub_text(g_rec, "cCiuRec", int(factura.c_ciu_rec))
    _sub_text(g_rec, "dDesCiuRec", factura.d_des_ciu_rec.strip())
    if getattr(factura, "receptor_tel", None):
        _sub_text(g_rec, "dTelRec", factura.receptor_tel.strip())
    if getattr(factura, "d_cod_cliente", None):
        _sub_text(g_rec, "dCodCliente", factura.d_cod_cliente.strip())

    # ---------------------------------------------------------------------------
    # gDtipDE
    # ---------------------------------------------------------------------------
    g_dtip = _el(de, "gDtipDE")

    # Documento de tipo Factura (1, 2)
    if i_ti_de in (1, 2, 3):
        g_fe = _el(g_dtip, "gCamFE")
        _sub_text(g_fe, "iIndPres", 1)
        _sub_text(g_fe, "dDesIndPres", "Operación presencial")

        g_cond = _el(g_dtip, "gCamCond")
        _sub_text(g_cond, "iCondOpe", factura.i_cond_ope)
        _sub_text(g_cond, "dDCondOpe", "Contado" if factura.i_cond_ope == 1 else "Crédito")
        if factura.i_cond_ope == 2:
            g_pc = _el(g_cond, "gPagCred")
            _sub_text(g_pc, "iCondCred", 1)
            _sub_text(g_pc, "dDCondCred", "Plazo")
            _sub_text(g_pc, "dPlazoCre", getattr(factura, "d_plazo_cre", "30") or "30")

    # Documento de tipo Autofactura (4)
    elif i_ti_de == 4:
        g_ae = _el(g_dtip, "gCamAE")
        _sub_text(g_ae, "iNatVen", 1)
        _sub_text(g_ae, "dDesNatVen", "No domiciliado")
        _sub_text(g_ae, "iTipIDVen", 1)
        _sub_text(g_ae, "dDTipIDVen", "Cédula paraguaya")
        _sub_text(g_ae, "dNumIDVen", rec_ruc_raw)
        _sub_text(g_ae, "dNomVen", factura.receptor_nombre.strip())
        _sub_text(g_ae, "dDirVen", factura.receptor_dir.strip() or "Sin direccion")
        _sub_text(g_ae, "dNumCasVen", "0")
        _sub_text(g_ae, "cDepVen", int(factura.c_dep_rec))
        _sub_text(g_ae, "dDesDepVen", factura.d_des_dep_rec.strip())
        _sub_text(g_ae, "cDisVen", int(factura.c_dis_rec))
        _sub_text(g_ae, "dDesDisVen", factura.d_des_dis_rec.strip())
        _sub_text(g_ae, "cCiuVen", int(factura.c_ciu_rec))
        _sub_text(g_ae, "dDesCiuVen", factura.d_des_ciu_rec.strip())

    # Documento de tipo Nota de Crédito / Débito (5, 6)
    elif i_ti_de in (5, 6):
        g_nc = _el(g_dtip, "gCamNCDE")
        motivo_nc = getattr(factura, "motivo_emision_nc", 1) or 1
        _sub_text(g_nc, "iMotEmi", motivo_nc)
        _sub_text(g_nc, "dDesMotEmi", MOTIVO_NC_DESC.get(motivo_nc, "Devolución"))

        # Documento Asociado obligatorio en NC/ND
        cdc_asoc = getattr(factura, "cdc_asociado", "") or ""
        tipo_asoc = getattr(factura, "tipo_doc_asociado", 1) or 1

        g_asoc = _el(g_dtip, "gCamDEAsoc")
        _sub_text(g_asoc, "iTipDocAso", tipo_asoc)
        _sub_text(g_asoc, "dDesTipDocAso", "Electrónico" if tipo_asoc == 1 else "Impreso")
        if tipo_asoc == 1 and cdc_asoc:
            _sub_text(g_asoc, "dCdCDERef", cdc_asoc.strip())
        else:
            _sub_text(g_asoc, "dNTim", getattr(factura, "timbrado_doc_asociado", "12345678") or "12345678")
            _sub_text(g_asoc, "dEst", "001")
            _sub_text(g_asoc, "dPunExp", "001")
            _sub_text(g_asoc, "dNumDoc", getattr(factura, "numero_doc_asociado", "0000001") or "0000001")
            _sub_text(g_asoc, "iTipoDocAso", 1)
            _sub_text(g_asoc, "dDTipoDocAso", "Factura")
            _sub_text(g_asoc, "dFecEmi", getattr(factura, "fecha_doc_asociado", d_fe_emi_str[:10]) or d_fe_emi_str[:10])

        g_cond = _el(g_dtip, "gCamCond")
        _sub_text(g_cond, "iCondOpe", 1)
        _sub_text(g_cond, "dDCondOpe", "Contado")

    # Documento de tipo Nota de Remisión (7)
    elif i_ti_de == 7:
        g_nr = _el(g_dtip, "gCamNRE")
        _sub_text(g_nr, "iMotEmiNR", 1)
        _sub_text(g_nr, "dDesMotEmiNR", "Traslado por venta")
        _sub_text(g_nr, "iRespFlete", 1)
        _sub_text(g_nr, "dFecIniTras", d_fe_emi_str[:10])
        _sub_text(g_nr, "dFecFinTras", d_fe_emi_str[:10])
        _sub_text(g_nr, "dPaisDest", "PRY")
        _sub_text(g_nr, "dDesPaisDest", "Paraguay")

    # ---------------------------------------------------------------------------
    # gCamItem (Líneas de Detalle)
    # ---------------------------------------------------------------------------
    for i, ln in enumerate(lineas):
        det = detalles_iva[i]
        g_item = _el(g_dtip, "gCamItem")
        _sub_text(g_item, "dCodInt", ln.d_cod_int.strip())
        _sub_text(g_item, "dDesProSer", ln.d_des_pro_ser.strip())
        _sub_text(g_item, "cUniMed", ln.c_uni_med)
        _sub_text(g_item, "dDesUniMed", ln.d_des_uni_med.strip())
        _sub_text(g_item, "dCantProSer", ln.d_cant_pro_ser)
        if getattr(ln, "d_inf_item", None):
            _sub_text(g_item, "dInfItem", ln.d_inf_item.strip())

        g_val = _el(g_item, "gValorItem")
        _sub_text(g_val, "dPUniProSer", ln.d_p_uni_pro_ser)
        if moneda != "PYG" and tipo_cambio > 1:
            _sub_text(g_val, "dTiCamIt", int(round(tipo_cambio)) if tipo_cambio.is_integer() else tipo_cambio)
        _sub_text(g_val, "dTotBruOpeItem", det.d_tot_bru_ope_item)

        g_vr = _el(g_val, "gValorRestaItem")
        _sub_text(g_vr, "dDescItem", det.d_desc_item)
        _sub_text(g_vr, "dPorcDesIt", det.d_porc_des_it)
        _sub_text(g_vr, "dDescGloItem", det.d_desc_glo_item)
        _sub_text(g_vr, "dTotOpeItem", det.d_tot_ope_item)

        # gCamIVA
        g_iva = _el(g_item, "gCamIVA")
        _sub_text(g_iva, "iAfecIVA", ln.i_afec_iva)
        afec_desc = "Gravado IVA" if ln.i_afec_iva == 1 else ("Exonerado" if ln.i_afec_iva == 2 else "Exento")
        _sub_text(g_iva, "dDesAfecIVA", afec_desc)
        _sub_text(g_iva, "dPropIVA", det.d_prop_iva)
        _sub_text(g_iva, "dTasaIVA", det.d_tasa_iva)
        _sub_text(g_iva, "dBasGravIVA", det.d_bas_grav_iva)
        _sub_text(g_iva, "dLiqIVAItem", det.d_liq_iva_item)
        if det.d_bas_exe_item > 0:
            _sub_text(g_iva, "dBasExe", det.d_bas_exe_item)

    # gTransp opcional
    if incluir_transporte_ejemplo or i_ti_de in (2, 7):
        g_tr = _el(g_dtip, "gTransp")
        _sub_text(g_tr, "iModTrans", 1)
        _sub_text(g_tr, "dDesModTrans", "Terrestre")
        _sub_text(g_tr, "iRespFlete", 1)

    # ---------------------------------------------------------------------------
    # gTotSub (Totales y Liquidaciones)
    # ---------------------------------------------------------------------------
    g_tot = _el(de, "gTotSub")
    _sub_text(g_tot, "dSubExe", tot.d_sub_exe)
    _sub_text(g_tot, "dSubExo", tot.d_sub_exo)
    _sub_text(g_tot, "dSub5", tot.d_sub5)
    _sub_text(g_tot, "dSub10", tot.d_sub10)
    _sub_text(g_tot, "dTotOpe", tot.d_tot_ope)
    _sub_text(g_tot, "dTotDesc", tot.d_tot_desc)
    _sub_text(g_tot, "dTotDescGlotem", tot.d_tot_desc_glotem)
    _sub_text(g_tot, "dTotAntItem", tot.d_tot_ant_item)
    _sub_text(g_tot, "dTotAnt", tot.d_tot_ant)
    _sub_text(g_tot, "dPorcDescTotal", tot.d_porc_desc_total)
    _sub_text(g_tot, "dDescTotal", tot.d_desc_total)
    _sub_text(g_tot, "dAnticipo", tot.d_anticipo)
    _sub_text(g_tot, "dRedon", tot.d_redon)
    _sub_text(g_tot, "dTotGralOpe", tot.d_tot_gral_ope)
    _sub_text(g_tot, "dIVA5", tot.d_iva5)
    _sub_text(g_tot, "dIVA10", tot.d_iva10)
    _sub_text(g_tot, "dTotIVA", tot.d_tot_iva)
    _sub_text(g_tot, "dBaseGrav5", tot.d_base_grav5)
    _sub_text(g_tot, "dBaseGrav10", tot.d_base_grav10)
    _sub_text(g_tot, "dTBasGraIVA", tot.d_t_bas_gra_iva)

    # ---------------------------------------------------------------------------
    # Signature Placeholder
    # ---------------------------------------------------------------------------
    sig = ET.SubElement(rde, f"{{{DSIG}}}Signature")
    sig.set("xmlns", DSIG)
    si = ET.SubElement(sig, f"{{{DSIG}}}SignedInfo")
    ET.SubElement(si, f"{{{DSIG}}}CanonicalizationMethod").set(
        "Algorithm", "http://www.w3.org/2001/10/xml-exc-c14n#"
    )
    ET.SubElement(si, f"{{{DSIG}}}SignatureMethod").set(
        "Algorithm", "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"
    )
    ref = ET.SubElement(si, f"{{{DSIG}}}Reference")
    ref.set("URI", f"#{cdc}")
    ET.SubElement(ref, f"{{{DSIG}}}DigestMethod").set("Algorithm", "http://www.w3.org/2001/04/xmlenc#sha256")
    dv = ET.SubElement(ref, f"{{{DSIG}}}DigestValue")
    dv.text = "PENDIENTE_FIRMA_DIGITAL"

    sv = ET.SubElement(sig, f"{{{DSIG}}}SignatureValue")
    sv.text = "PENDIENTE_FIRMA_DIGITAL"
    ki = ET.SubElement(sig, f"{{{DSIG}}}KeyInfo")
    xd = ET.SubElement(ki, f"{{{DSIG}}}X509Data")
    xc = ET.SubElement(xd, f"{{{DSIG}}}X509Certificate")
    xc.text = "CERTIFICADO_DIGITAL_PKCS12"

    # ---------------------------------------------------------------------------
    # gCamFuFD (Código QR oficial)
    # ---------------------------------------------------------------------------
    g_qr = _el(rde, "gCamFuFD")
    _sub_text(g_qr, "dCarQR", factura.d_car_qr or "")

    ET.register_namespace("", NS)
    ET.register_namespace("xsi", XSI)

    xml_bytes = ET.tostring(rde, encoding="utf-8", xml_declaration=True, default_namespace=None)
    return xml_bytes.decode("utf-8")
