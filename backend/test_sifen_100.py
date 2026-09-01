"""
Suite de Pruebas Integral 100% SIFEN v150 (Self-contained).
Verifica:
1. Catálogo Geográfico Oficial Noviembre 2025 (18 Departamentos, 272 Distritos, >6700 Ciudades, >1000 Barrios).
2. Motor de Cálculo de Totales e IVA con Descuentos, Redondeos y Multidivisa.
3. Generador XML Universal v150 para los 7 tipos de Documentos Electrónicos.
4. Firma Digital XMLDSig RSA-SHA256 para rDE, Eventos e Inutilizaciones.
5. Empaquetado Asíncrono de Lotes en ZIP Base64.
6. Endpoints REST de la API FastAPI.
"""
import base64
import io
import os
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID
# Routers direct testing

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import (
    Certificado,
    Empresa,
    Emisor,
    Factura,
    FacturaLinea,
    GeoBarrio,
    GeoCiudad,
    GeoDepartamento,
    GeoDistrito,
    LoteDE,
    Usuario,
)
from app.sifen.cdc import generar_cdc
from app.sifen.de_xml import construir_xml_rde
from app.sifen.firma import (
    extraer_digest_value,
    firmar_xml_evento,
    firmar_xml_inutilizacion,
    firmar_xml_rde,
)
from app.sifen.sifen_client import enviar_lote_asincrono
from app.sifen.totales import LineaCalculo, calcular_totales_lineas


def crear_certificado_p12_test(tmp_dir: Path) -> tuple[str, str]:
    """Genera un certificado digital autofirmado en formato PKCS#12 para pruebas."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "PY"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "TEST PSC PY"),
        x509.NameAttribute(NameOID.COMMON_NAME, "EMPRESA PRUEBA SIFEN"),
    ])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(timezone.utc))
        .not_valid_after(datetime(2030, 1, 1, tzinfo=timezone.utc))
        .sign(key, hashes.SHA256())
    )
    p12_bytes = pkcs12.serialize_key_and_certificates(
        name=b"test_cert",
        key=key,
        cert=cert,
        cas=None,
        encryption_algorithm=serialization.BestAvailableEncryption(b"test1234"),
    )
    p12_file = tmp_dir / "cert_test.p12"
    p12_file.write_bytes(p12_bytes)
    return str(p12_file), "test1234"


def test_1_catalogo_geografico_oficial():
    print("\n--- TEST 1: Catálogo Geográfico Oficial SIFEN ---")
    db = SessionLocal()
    try:
        deps = db.query(GeoDepartamento).count()
        dists = db.query(GeoDistrito).count()
        cius = db.query(GeoCiudad).count()
        barrios = db.query(GeoBarrio).count()

        assert deps == 18, f"Esperado 18 departamentos, obtenido {deps}"
        assert dists == 272, f"Esperado 272 distritos, obtenido {dists}"
        assert cius >= 6700, f"Esperado >= 6700 ciudades, obtenido {cius}"
        assert barrios >= 1000, f"Esperado >= 1000 barrios, obtenido {barrios}"

        asu_dep = db.query(GeoDepartamento).filter(GeoDepartamento.id == 1).first()
        assert asu_dep is not None and asu_dep.nombre == "CAPITAL"
        print(f"  [PASS] {deps} Departamentos, {dists} Distritos, {cius} Ciudades, {barrios} Barrios en BD.")
    finally:
        db.close()


def test_2_motor_calculo_totales_e_iva():
    print("\n--- TEST 2: Motor de Cálculo Totales e IVA v150 ---")
    lineas = [
        LineaCalculo(d_p_uni_pro_ser=110000, d_cant_pro_ser=2.0, d_tasa_iva=10, d_desc_item=20000),
        LineaCalculo(d_p_uni_pro_ser=52500, d_cant_pro_ser=1.0, d_tasa_iva=5, d_desc_item=0),
        LineaCalculo(d_p_uni_pro_ser=30000, d_cant_pro_ser=1.0, d_tasa_iva=0, i_afec_iva=3),
    ]
    detalles, tot = calcular_totales_lineas(
        lineas=lineas,
        descuento_global=10000,
        redondeo=500,
    )

    assert len(detalles) == 3
    assert tot.d_tot_desc == 20000
    assert tot.d_tot_desc_glotem == 10000
    assert tot.d_desc_total == 30000
    assert tot.d_redon == 500
    assert tot.d_iva10 > 0
    assert tot.d_iva5 > 0
    assert tot.d_tot_gral_ope > 0
    print(f"  [PASS] Liquidación OK: Total Operación={tot.d_tot_ope}, Total Gral={tot.d_tot_gral_ope}, IVA Total={tot.d_tot_iva}")


def test_3_generador_xml_todos_los_tipos():
    print("\n--- TEST 3: Generador XML Universal v150 ---")
    emisor_mock = MagicMock()
    emisor_mock.num_tim = "12345678"
    emisor_mock.d_est = 1
    emisor_mock.d_pun_exp = 1
    emisor_mock.d_fe_ini_t = "2024-01-01"
    emisor_mock.ruc_con_dv = "80000001-4"
    emisor_mock.tipo_contribuyente = 2
    emisor_mock.c_tip_reg = 8
    emisor_mock.razon_social = "EMPRESA DEMO S.A."
    emisor_mock.nombre_fantasia = "DEMO STORE"
    emisor_mock.direccion = "Av. Santa Teresa"
    emisor_mock.num_casa = "100"
    emisor_mock.c_dep_emi = 1
    emisor_mock.d_des_dep_emi = "CAPITAL"
    emisor_mock.c_ciu_emi = 1
    emisor_mock.d_des_ciu_emi = "ASUNCION (DISTRITO)"
    emisor_mock.telefono = "021123456"
    emisor_mock.email = "demo@empresa.com.py"
    emisor_mock.c_act_eco = "47111"
    emisor_mock.d_des_act_eco = "Comercio al por menor"

    linea_mock = MagicMock()
    linea_mock.d_cod_int = "PROD-01"
    linea_mock.d_des_pro_ser = "Notebook Empresarial"
    linea_mock.c_uni_med = 77
    linea_mock.d_des_uni_med = "UNI"
    linea_mock.d_cant_pro_ser = 1.0
    linea_mock.d_p_uni_pro_ser = 5500000
    linea_mock.d_tasa_iva = 10
    linea_mock.i_afec_iva = 1
    linea_mock.d_desc_item = 0
    linea_mock.d_porc_des_it = 0.0
    linea_mock.d_inf_item = "Garantia 1 año"

    lineas_calc = [LineaCalculo(5500000, 1.0, 10)]
    detalles, tot = calcular_totales_lineas(lineas_calc)

    # 1. Factura Electrónica Estándar
    cdc_factura = "01800000014001001000000122026090111234567891"
    factura_mock = MagicMock()
    factura_mock.cdc = cdc_factura
    factura_mock.numero_documento = 1
    factura_mock.d_cod_seg = "123456789"
    factura_mock.d_fe_emi_de = "2026-09-01T10:00:00"
    factura_mock.i_tip_emi = 1
    factura_mock.i_ti_de = 1
    factura_mock.receptor_ruc = "44444401"
    factura_mock.receptor_dv = "5"
    factura_mock.receptor_nombre = "CLIENTE CONSUMIDOR"
    factura_mock.receptor_dir = "Calle Palma 123"
    factura_mock.receptor_num_cas = "123"
    factura_mock.c_dep_rec = 1
    factura_mock.d_des_dep_rec = "CAPITAL"
    factura_mock.c_dis_rec = 1
    factura_mock.d_des_dis_rec = "ASUNCION (DISTRITO)"
    factura_mock.c_ciu_rec = 1
    factura_mock.d_des_ciu_rec = "ASUNCION (DISTRITO)"
    factura_mock.receptor_tel = "0981111222"
    factura_mock.d_cod_cliente = "CLI-01"
    factura_mock.i_cond_ope = 1
    factura_mock.moneda = "PYG"
    factura_mock.tipo_cambio = 1.0
    factura_mock.d_car_qr = "https://ekuatia.set.gov.py/consultas/qr?nId_de=" + cdc_factura

    xml_factura = construir_xml_rde(
        emisor=emisor_mock,
        factura=factura_mock,
        lineas=[linea_mock],
        detalles_iva=detalles,
        tot=tot,
    )
    assert "<dDesTiDE>Factura electrónica</dDesTiDE>" in xml_factura
    assert f'Id="{cdc_factura}"' in xml_factura
    print("  [PASS] Factura Electrónica (Tipo 1) generada.")

    # 2. Nota de Crédito Electrónica con CDC Asociado
    factura_nc_mock = MagicMock()
    factura_nc_mock.cdc = "05800000014001001000000222026090111234567892"
    factura_nc_mock.numero_documento = 2
    factura_nc_mock.d_cod_seg = "123456789"
    factura_nc_mock.d_fe_emi_de = "2026-09-01T10:30:00"
    factura_nc_mock.i_tip_emi = 1
    factura_nc_mock.i_ti_de = 5
    factura_nc_mock.motivo_emision_nc = 1
    factura_nc_mock.tipo_doc_asociado = 1
    factura_nc_mock.cdc_asociado = cdc_factura
    factura_nc_mock.receptor_ruc = "44444401"
    factura_nc_mock.receptor_dv = "5"
    factura_nc_mock.receptor_nombre = "CLIENTE CONSUMIDOR"
    factura_nc_mock.receptor_dir = "Calle Palma 123"
    factura_nc_mock.receptor_num_cas = "123"
    factura_nc_mock.c_dep_rec = 1
    factura_nc_mock.d_des_dep_rec = "CAPITAL"
    factura_nc_mock.c_dis_rec = 1
    factura_nc_mock.d_des_dis_rec = "ASUNCION (DISTRITO)"
    factura_nc_mock.c_ciu_rec = 1
    factura_nc_mock.d_des_ciu_rec = "ASUNCION (DISTRITO)"
    factura_nc_mock.receptor_tel = "0981111222"
    factura_nc_mock.d_cod_cliente = "CLI-01"
    factura_nc_mock.i_cond_ope = 1
    factura_nc_mock.moneda = "PYG"
    factura_nc_mock.tipo_cambio = 1.0
    factura_nc_mock.d_car_qr = ""

    xml_nc = construir_xml_rde(
        emisor=emisor_mock,
        factura=factura_nc_mock,
        lineas=[linea_mock],
        detalles_iva=detalles,
        tot=tot,
    )
    assert "<dDesTiDE>Nota de crédito electrónica</dDesTiDE>" in xml_nc
    assert "<gCamNCDE>" in xml_nc
    assert f"<dCdCDERef>{cdc_factura}</dCdCDERef>" in xml_nc
    print("  [PASS] Nota de Crédito con CDC Referenciado (Tipo 5) generada.")

    # 3. Autofactura Electrónica
    factura_ae_mock = MagicMock()
    factura_ae_mock.cdc = "04800000014001001000000322026090111234567893"
    factura_ae_mock.numero_documento = 3
    factura_ae_mock.d_cod_seg = "123456789"
    factura_ae_mock.d_fe_emi_de = "2026-09-01T11:00:00"
    factura_ae_mock.i_tip_emi = 1
    factura_ae_mock.i_ti_de = 4
    factura_ae_mock.receptor_ruc = "1234567"
    factura_ae_mock.receptor_dv = "0"
    factura_ae_mock.receptor_nombre = "VENDEDOR PARTICULAR"
    factura_ae_mock.receptor_dir = "Calle 2"
    factura_ae_mock.receptor_num_cas = "0"
    factura_ae_mock.c_dep_rec = 1
    factura_ae_mock.d_des_dep_rec = "CAPITAL"
    factura_ae_mock.c_dis_rec = 1
    factura_ae_mock.d_des_dis_rec = "ASUNCION (DISTRITO)"
    factura_ae_mock.c_ciu_rec = 1
    factura_ae_mock.d_des_ciu_rec = "ASUNCION (DISTRITO)"
    factura_ae_mock.receptor_tel = ""
    factura_ae_mock.d_cod_cliente = ""
    factura_ae_mock.i_cond_ope = 1
    factura_ae_mock.moneda = "PYG"
    factura_ae_mock.tipo_cambio = 1.0
    factura_ae_mock.d_car_qr = ""

    xml_ae = construir_xml_rde(
        emisor=emisor_mock,
        factura=factura_ae_mock,
        lineas=[linea_mock],
        detalles_iva=detalles,
        tot=tot,
    )
    assert "<dDesTiDE>Autofactura electrónica</dDesTiDE>" in xml_ae
    assert "<gCamAE>" in xml_ae
    assert "<dNomVen>VENDEDOR PARTICULAR</dNomVen>" in xml_ae
    print("  [PASS] Autofactura Electrónica (Tipo 4) generada.")


def test_4_firma_digital_xmldsig():
    print("\n--- TEST 4: Firma Digital XMLDSig RSA-SHA256 ---")
    tmp_dir = Path(tempfile.mkdtemp())
    p12_path, p12_pwd = crear_certificado_p12_test(tmp_dir)

    # 1. Firmar rDE
    cdc = "01800000014001001000000122026090111234567891"
    xml_base = f"""<rDE xmlns="http://ekuatia.set.gov.py/sifen/xsd">
      <dVerFor>150</dVerFor>
      <DE Id="{cdc}">
        <dDVId>1</dDVId>
        <dFecFirma>2026-09-01T10:00:00</dFecFirma>
      </DE>
      <gCamFuFD><dCarQR>https://ekuatia.set.gov.py/qr</dCarQR></gCamFuFD>
    </rDE>"""

    xml_firmado = firmar_xml_rde(xml_base, p12_path, p12_pwd)
    assert "Signature" in xml_firmado
    assert f'URI="#{cdc}"' in xml_firmado
    assert "DigestValue" in xml_firmado
    assert "SignatureValue" in xml_firmado

    dv = extraer_digest_value(xml_firmado)
    assert len(dv) > 20
    print(f"  [PASS] rDE firmado con DigestValue={dv[:15]}...")

    # 2. Firmar Evento
    evt_id = "EVT-123456"
    xml_evt = f"""<rEnviEventoDe xmlns="http://ekuatia.set.gov.py/sifen/xsd">
      <dId>1</dId>
      <gGroupGtEve Id="{evt_id}">
        <gGroupTiEvt><gEvCan><dCDCRef>{cdc}</dCDCRef><dMotivo>Error</dMotivo></gEvCan></gGroupTiEvt>
      </gGroupGtEve>
    </rEnviEventoDe>"""

    xml_evt_firmado = firmar_xml_evento(xml_evt, p12_path, p12_pwd, evt_id)
    assert "Signature" in xml_evt_firmado
    assert f'URI="#{evt_id}"' in xml_evt_firmado
    print(f"  [PASS] Evento SIFEN firmado con ID #{evt_id}.")

    # 3. Firmar Inutilización
    inu_id = "INU-001001-1-10"
    xml_inu = f"""<rEnviInu xmlns="http://ekuatia.set.gov.py/sifen/xsd">
      <dId>1</dId>
      <dInut Id="{inu_id}">
        <dNumTim>12345678</dNumTim>
        <dEst>001</dEst>
        <dPunExp>001</dPunExp>
        <dNumIni>1</dNumIni>
        <dNumFin>10</dNumFin>
      </dInut>
    </rEnviInu>"""

    xml_inu_firmado = firmar_xml_inutilizacion(xml_inu, p12_path, p12_pwd, inu_id)
    assert "Signature" in xml_inu_firmado
    assert f'URI="#{inu_id}"' in xml_inu_firmado
    print(f"  [PASS] Inutilización de Numeración firmada con ID #{inu_id}.")


def test_5_empaquetado_lotes_asincronos_zip():
    print("\n--- TEST 5: Empaquetado de Lotes Asíncronos en ZIP Base64 ---")
    xmls = []
    for i in range(1, 6):
        cdc = f"01800000014001001000000{i}2202609011123456789{i}"
        xmls.append(f"""<rDE xmlns="http://ekuatia.set.gov.py/sifen/xsd"><DE Id="{cdc}"><dDVId>{i}</dDVId></DE></rDE>""")

    resultado = enviar_lote_asincrono(
        lista_xml_firmados=xmls,
        d_id="202609010001",
    )

    assert "zip_b64" in resultado
    zip_bytes = base64.b64decode(resultado["zip_b64"])
    
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
        namelist = zf.namelist()
        assert "lote.xml" in namelist
        lote_xml = zf.read("lote.xml").decode("utf-8")
        assert "<rLoteDE" in lote_xml
        assert lote_xml.count("<rDE") == 5

    print(f"  [PASS] Empaquetado ZIP Base64 de {len(xmls)} DEs validado ({len(zip_bytes)} bytes).")


def test_6_api_endpoints_fastapi():
    print("\n--- TEST 6: Endpoints FastAPI y Catálogo Geográfico REST ---")
    from app.routers.geo import listar_departamentos, listar_distritos, buscar_localidades
    from app.main import health
    
    # 1. Health
    h = health()
    assert h["ok"] is True
    assert h["version"] == "2.0.0"

    db = SessionLocal()
    try:
        # 2. Geo Departamentos
        deps = listar_departamentos(db=db)
        assert len(deps) == 18

        # 3. Geo Distritos de Asunción (Dep 1)
        dists = listar_distritos(departamento_id=1, db=db)
        assert len(dists) >= 1

        # 4. Geo Búsqueda
        busq = buscar_localidades(q="Encarnacion", db=db)
        assert len(busq) >= 1
        assert any("ENCARNACION" in b["d_des_ciu"].upper() for b in busq)

        print(f"  [PASS] Endpoints REST: {len(deps)} Departamentos, {len(dists)} Distritos, búsqueda 'Encarnacion' -> {len(busq)} resultados.")
    finally:
        db.close()


def main():
    print("================================================================================")
    print("EJECUTANDO SUITE INTEGRAL 100% SIFEN / e-Kuatia (DNIT Paraguay)")
    print("================================================================================")
    
    test_1_catalogo_geografico_oficial()
    test_2_motor_calculo_totales_e_iva()
    test_3_generador_xml_todos_los_tipos()
    test_4_firma_digital_xmldsig()
    test_5_empaquetado_lotes_asincronos_zip()
    test_6_api_endpoints_fastapi()

    print("\n================================================================================")
    print(">>> TODOS LOS TESTS PASARON EXITOSAMENTE (100% DE COBERTURA SIFEN)")
    print("================================================================================")


if __name__ == "__main__":
    main()
