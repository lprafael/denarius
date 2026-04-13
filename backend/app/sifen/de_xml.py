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


def _el(parent: ET.Element, tag: str, text: str | int | float | None = None) -> ET.Element:
    e = ET.SubElement(parent, f"{{{NS}}}{tag}")
    if text is not None:
        e.text = str(text)
    return e


def _sub_text(parent: ET.Element, tag: str, value: str | int | float | None) -> None:
    if value is not None and str(value).strip() != "":
        _el(parent, tag, value)


def construir_xml_rde(
    *,
    emisor: "Emisor",
    factura: "Factura",
    lineas: list["FacturaLinea"],
    detalles_iva: list[LineaIVADetail],
    tot: TotalesDE,
    incluir_transporte_ejemplo: bool = False,
) -> str:
    """Genera el XML rDE según la estructura del ejemplo oficial (versión 150). Sin firma digital real."""
    cdc = factura.cdc
    fe_emi = factura.d_fe_emi_de
    if isinstance(fe_emi, datetime):
        d_fe_emi_str = fe_emi.strftime("%Y-%m-%dT%H:%M:%S")
    else:
        d_fe_emi_str = str(fe_emi)

    rde = ET.Element(f"{{{NS}}}rDE")
    rde.set(f"{{{XSI}}}schemaLocation", "https://ekuatia.set.gov.py/sifen/xsd siRecepDE_v150.xsd")

    _sub_text(rde, "dVerFor", settings.d_ver_for)

    de = ET.SubElement(rde, f"{{{NS}}}DE")
    de.set("Id", cdc)

    _sub_text(de, "dDVId", cdc[-1])
    _sub_text(de, "dFecFirma", d_fe_emi_str[:19])
    _sub_text(de, "dSisFact", 1)

    g_ope = _el(de, "gOpeDE")
    _sub_text(g_ope, "iTipEmi", factura.i_tip_emi)
    _sub_text(g_ope, "dDesTipEmi", "Normal" if factura.i_tip_emi == 1 else "Contingencia")
    _sub_text(g_ope, "dCodSeg", factura.d_cod_seg)
    _sub_text(g_ope, "dInfoEmi", 1)
    _sub_text(g_ope, "dInfoFisc", "Información de interés del Fisco respecto al DE")

    g_timb = _el(de, "gTimb")
    _sub_text(g_timb, "iTiDE", factura.i_ti_de)
    _sub_text(g_timb, "dDesTiDE", "Factura electrónica")
    _sub_text(g_timb, "dNumTim", emisor.num_tim)
    _sub_text(g_timb, "dEst", emisor.d_est)
    _sub_text(g_timb, "dPunExp", emisor.d_pun_exp)
    _sub_text(g_timb, "dNumDoc", factura.numero_documento)
    if emisor.d_serie_num:
        _sub_text(g_timb, "dSerieNum", emisor.d_serie_num)
    _sub_text(g_timb, "dFeIniT", emisor.d_fe_ini_t)

    g_dat = _el(de, "gDatGralOpe")
    _sub_text(g_dat, "dFeEmiDE", d_fe_emi_str)

    g_ope_com = _el(g_dat, "gOpeCom")
    _sub_text(g_ope_com, "iTipTra", 1)
    _sub_text(g_ope_com, "dDesTipTra", "Venta de mercadería")
    _sub_text(g_ope_com, "iTImp", 1)
    _sub_text(g_ope_com, "dDesTImp", "IVA")
    _sub_text(g_ope_com, "cMoneOpe", "PYG")
    _sub_text(g_ope_com, "dDesMoneOpe", "Guarani")

    g_emis = _el(g_dat, "gEmis")
    ruc_parts = emisor.ruc_con_dv.split("-")
    _sub_text(g_emis, "dRucEm", ruc_parts[0].zfill(8))
    _sub_text(g_emis, "dDVEmi", ruc_parts[1] if len(ruc_parts) > 1 else "")
    _sub_text(g_emis, "iTipCont", emisor.tipo_contribuyente)
    _sub_text(g_emis, "cTipReg", emisor.c_tip_reg)
    _sub_text(g_emis, "dNomEmi", emisor.razon_social)
    _sub_text(g_emis, "dDirEmi", emisor.direccion)
    _sub_text(g_emis, "dNumCas", emisor.num_casa)
    _sub_text(g_emis, "cDepEmi", emisor.c_dep_emi)
    _sub_text(g_emis, "dDesDepEmi", emisor.d_des_dep_emi)
    _sub_text(g_emis, "cCiuEmi", emisor.c_ciu_emi)
    _sub_text(g_emis, "dDesCiuEmi", emisor.d_des_ciu_emi)
    _sub_text(g_emis, "dTelEmi", emisor.telefono)
    _sub_text(g_emis, "dEmailE", emisor.email)
    g_act = _el(g_emis, "gActEco")
    _sub_text(g_act, "cActEco", emisor.c_act_eco)
    _sub_text(g_act, "dDesActEco", emisor.d_des_act_eco)

    g_rec = _el(g_dat, "gDatRec")
    _sub_text(g_rec, "iNatRec", 1)
    _sub_text(g_rec, "iTiOpe", 1)
    _sub_text(g_rec, "cPaisRec", "PRY")
    _sub_text(g_rec, "dDesPaisRe", "Paraguay")
    _sub_text(g_rec, "iTiContRec", 2)
    _sub_text(g_rec, "dRucRec", factura.receptor_ruc.zfill(8))
    _sub_text(g_rec, "dDVRec", factura.receptor_dv)
    _sub_text(g_rec, "dNomRec", factura.receptor_nombre)
    _sub_text(g_rec, "dDirRec", factura.receptor_dir)
    _sub_text(g_rec, "dNumCasRec", factura.receptor_num_cas)
    _sub_text(g_rec, "cDepRec", factura.c_dep_rec)
    _sub_text(g_rec, "dDesDepRec", factura.d_des_dep_rec)
    _sub_text(g_rec, "cDisRec", factura.c_dis_rec)
    _sub_text(g_rec, "dDesDisRec", factura.d_des_dis_rec)
    _sub_text(g_rec, "cCiuRec", factura.c_ciu_rec)
    _sub_text(g_rec, "dDesCiuRec", factura.d_des_ciu_rec)
    _sub_text(g_rec, "dTelRec", factura.receptor_tel)
    _sub_text(g_rec, "dCodCliente", factura.d_cod_cliente)

    g_dtip = _el(de, "gDtipDE")
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
        _sub_text(g_pc, "dPlazoCre", factura.d_plazo_cre or "30")

    for i, ln in enumerate(lineas):
        det = detalles_iva[i]
        g_item = _el(g_dtip, "gCamItem")
        _sub_text(g_item, "dCodInt", ln.d_cod_int)
        _sub_text(g_item, "dDesProSer", ln.d_des_pro_ser)
        _sub_text(g_item, "cUniMed", ln.c_uni_med)
        _sub_text(g_item, "dDesUniMed", ln.d_des_uni_med)
        _sub_text(g_item, "dCantProSer", ln.d_cant_pro_ser)
        g_val = _el(g_item, "gValorItem")
        _sub_text(g_val, "dPUniProSer", ln.d_p_uni_pro_ser)
        _sub_text(g_val, "dTotBruOpeItem", det.d_tot_bru_ope_item)
        g_vr = _el(g_val, "gValorRestaItem")
        _sub_text(g_vr, "dDescItem", 0)
        _sub_text(g_vr, "dPorcDesIt", 0)
        _sub_text(g_vr, "dDescGloItem", 0)
        _sub_text(g_vr, "dTotOpeItem", det.d_tot_bru_ope_item)
        g_iva = _el(g_item, "gCamIVA")
        _sub_text(g_iva, "iAfecIVA", ln.i_afec_iva)
        _sub_text(g_iva, "dDesAfecIVA", "Gravado IVA" if ln.d_tasa_iva else "Exento")
        if ln.d_tasa_iva in (5, 10):
            _sub_text(g_iva, "dPropIVA", 100)
            _sub_text(g_iva, "dTasaIVA", ln.d_tasa_iva)
            _sub_text(g_iva, "dBasGravIVA", det.d_bas_grav_iva)
            _sub_text(g_iva, "dLiqIVAItem", det.d_liq_iva_item)
        else:
            _sub_text(g_iva, "dPropIVA", 0)
            _sub_text(g_iva, "dTasaIVA", 0)
            _sub_text(g_iva, "dBasGravIVA", 0)
            _sub_text(g_iva, "dLiqIVAItem", 0)

    if incluir_transporte_ejemplo:
        g_esp = _el(g_dtip, "gCamEsp")
        g_ga = _el(g_esp, "gGrupAdi")
        _sub_text(g_ga, "dCiclo", "REFERENCIA")
        _sub_text(g_ga, "dFecIniC", d_fe_emi_str[:10])
        _sub_text(g_ga, "dFecFinC", d_fe_emi_str[:10])
    g_tr = _el(g_dtip, "gTransp")
    _sub_text(g_tr, "iModTrans", 1)
    _sub_text(g_tr, "dDesModTrans", "Terrestre")
    _sub_text(g_tr, "iRespFlete", 2)
    if hasattr(factura, 'd_nu_desp_imp') and factura.d_nu_desp_imp:
        _sub_text(g_tr, "dNuDespImp", factura.d_nu_desp_imp)

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

    g_qr = _el(rde, "gCamFuFD")
    _sub_text(g_qr, "dCarQR", factura.d_car_qr or "")

    ET.register_namespace("", NS)
    ET.register_namespace("xsi", XSI)

    xml_bytes = ET.tostring(rde, encoding="utf-8", xml_declaration=True, default_namespace=None)
    return xml_bytes.decode("utf-8")
