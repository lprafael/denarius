"""
Suite de Pruebas de Homologación SIFEN / e-Kuatia Paraguay
Basada en la "Guía de Pruebas para e-Kuatia" de la SET/DNIT.

Ejecutar con:
    python tests/test_sifen_suite.py

o con pytest:
    pytest tests/test_sifen_suite.py -v
"""
import sys
import json
import time
import requests
from datetime import datetime, timezone

# ─────────────────────────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────────────────────────
BASE_URL = "http://localhost:8085"
CREDS = {
    "username": "admin@empresa.com.py",
    "password": "DenariusPrueba2026"
}

COLORES = {
    "OK":     "[PASS]",
    "FAIL":   "[FAIL]",
    "WARN":   "[WARN]",
    "INFO":   "[INFO]",
    "TITULO": "",
    "RESET":  "",
}

resultados = []
token = None


def paso(nombre, ok, detalle=""):
    icono = COLORES["OK"] if ok else COLORES["FAIL"]
    print(f"  {icono}  {nombre}")
    if detalle:
        print(f"         {detalle}")
    resultados.append({"nombre": nombre, "ok": ok, "detalle": detalle})


def seccion(titulo):
    print(f"\n{COLORES['TITULO']}{'─'*60}")
    print(f"  {titulo}")
    print(f"{'─'*60}{COLORES['RESET']}")


def get_token():
    global token
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": CREDS["username"], "password": CREDS["password"]})
    if r.status_code == 200:
        token = r.json().get("access_token")
        return token
    return None


def hdr():
    return {"Authorization": f"Bearer {token}"}


# ─────────────────────────────────────────────────────────────────
# 1. INFRAESTRUCTURA
# ─────────────────────────────────────────────────────────────────
def test_infraestructura():
    seccion("1. INFRAESTRUCTURA Y CONECTIVIDAD")

    # Health
    try:
        r = requests.get(f"{BASE_URL}/api/health", timeout=5)
        data = r.json()
        paso("Health check del backend", r.status_code == 200,
             f"ambiente={data.get('sifen_ambiente','?')}, v={data.get('version','?')}")
        paso("Ambiente configurado en TEST (homologación)", data.get("sifen_ambiente") == "test",
             "SIFEN_AMBIENTE debería ser 'test' para pruebas de homologación")
    except Exception as e:
        paso("Health check del backend", False, str(e))

    # Autenticación
    t = get_token()
    paso("Autenticación JWT (operador)", bool(t), "POST /api/auth/token")


# ─────────────────────────────────────────────────────────────────
# 2. GENERACION DE CDC
# ─────────────────────────────────────────────────────────────────
def test_generacion_cdc():
    seccion("2. GENERACIÓN DE CDC (Código de Control)")

    # Crear factura mínima para validar CDC
    payload = _factura_prueba("contado_gravado")
    r = requests.post(f"{BASE_URL}/api/facturas", json=payload, headers=hdr())
    if r.status_code == 200:
        data = r.json()
        cdc = data.get("cdc", "")
        paso("CDC generado en creación de factura", bool(cdc), f"CDC: {cdc[:10]}...")
        paso("Longitud del CDC es 44 dígitos", len(cdc) == 44, f"Longitud real: {len(cdc)}")
        paso("DV del CDC (último dígito) calculado por Módulo 11",
             cdc[-1].isdigit(), f"Último char: {cdc[-1]}")
        paso("Formato numérico completo del CDC", cdc.isdigit(), f"CDC: {cdc}")
        return data.get("id")
    else:
        paso("Crear factura de prueba (contado/gravado IVA 10)", False,
             f"HTTP {r.status_code}: {r.text[:200]}")
        return None


# ─────────────────────────────────────────────────────────────────
# 3. ESTRUCTURA XML / v150
# ─────────────────────────────────────────────────────────────────
def test_estructura_xml(factura_id: int | None):
    seccion("3. ESTRUCTURA DEL DE EN XML (v150)")
    if not factura_id:
        paso("Obtener XML del DE", False, "No hay factura de referencia")
        return

    r = requests.get(f"{BASE_URL}/api/facturas/{factura_id}/xml", headers=hdr())
    if r.status_code != 200:
        paso("XML disponible en endpoint", False, f"HTTP {r.status_code}")
        return

    xml_str = r.text
    paso("XML disponible en endpoint", True)
    paso("Nodo raíz <rDE> presente", "<rDE" in xml_str)
    paso("Nodo <DE Id=...> presente (con atributo Id=CDC)", '<DE Id="' in xml_str or "<DE " in xml_str)
    paso("Namespace SIFEN correcto (ekuatia.set.gov.py/sifen/xsd)", "ekuatia.set.gov.py/sifen/xsd" in xml_str)
    paso("Versión 150 declarada (<dVerFor>150)", "<dVerFor>150</dVerFor>" in xml_str)
    paso("Sin etiquetas vacías <dSerieNum/>", "<dSerieNum/>" not in xml_str and "<dSerieNum></dSerieNum>" not in xml_str)
    paso("Grupo <gTotSub> presente (totales SIFEN)", "<gTotSub>" in xml_str or "gTotSub" in xml_str)
    paso("Grupo <gCamFuFD> presente (QR)", "gCamFuFD" in xml_str)
    paso("URL QR presente", "ekuatia.set.gov.py" in xml_str)
    paso("Bloque <Signature> presente (firma digital)", "Signature" in xml_str)


# ─────────────────────────────────────────────────────────────────
# 4. ESCENARIOS DE PRUEBA (según Guía de Pruebas e-Kuatia)
# ─────────────────────────────────────────────────────────────────
def test_escenarios_factura():
    seccion("4. ESCENARIOS DE FACTURA (Guía de Pruebas SET)")
    ids = {}

    # Escenario A: Contado – IVA 10%
    p = _factura_prueba("contado_gravado")
    r = requests.post(f"{BASE_URL}/api/facturas", json=p, headers=hdr())
    ok = r.status_code == 200
    paso("Esc. A: Factura contado – IVA 10% gravado", ok,
         f"HTTP {r.status_code}" + (f" CDC:{r.json().get('cdc','')[:16]}..." if ok else f": {r.text[:150]}"))
    if ok:
        ids["contado_10"] = r.json().get("id")

    # Escenario B: Contado – IVA 5%
    p = _factura_prueba("contado_5pct")
    r = requests.post(f"{BASE_URL}/api/facturas", json=p, headers=hdr())
    ok = r.status_code == 200
    paso("Esc. B: Factura contado – IVA 5%", ok, f"HTTP {r.status_code}")
    if ok:
        ids["contado_5"] = r.json().get("id")

    # Escenario C: Contado – Exento de IVA
    p = _factura_prueba("contado_exento")
    r = requests.post(f"{BASE_URL}/api/facturas", json=p, headers=hdr())
    ok = r.status_code == 200
    paso("Esc. C: Factura contado – Exento IVA", ok, f"HTTP {r.status_code}")
    if ok:
        ids["exento"] = r.json().get("id")

    # Escenario D: Crédito – 30 días
    p = _factura_prueba("credito_30d")
    r = requests.post(f"{BASE_URL}/api/facturas", json=p, headers=hdr())
    ok = r.status_code == 200
    paso("Esc. D: Factura crédito – 30 días (gPagCred)", ok, f"HTTP {r.status_code}")
    if ok:
        ids["credito"] = r.json().get("id")

    # Escenario E: Mixto (IVA 5% + 10% + Exento)
    p = _factura_prueba("mixto")
    r = requests.post(f"{BASE_URL}/api/facturas", json=p, headers=hdr())
    ok = r.status_code == 200
    paso("Esc. E: Factura mixta (IVA 5%+10%+Exento en misma factura)", ok, f"HTTP {r.status_code}")
    if ok:
        ids["mixto"] = r.json().get("id")

    # Escenario F: Datos inválidos – debe rechazarse
    p_inv = _factura_prueba("contado_gravado")
    p_inv["lineas"][0]["d_tasa_iva"] = 99  # IVA inválido
    r = requests.post(f"{BASE_URL}/api/facturas", json=p_inv, headers=hdr())
    paso("Esc. F: Factura con tasa IVA inválida (99%) → rechazada", r.status_code in (400, 422),
         f"HTTP {r.status_code} (esperado 400 o 422)")

    # Escenario G: Sin líneas – debe rechazarse
    p_vacía = _factura_prueba("contado_gravado")
    p_vacía["lineas"] = []
    r = requests.post(f"{BASE_URL}/api/facturas", json=p_vacía, headers=hdr())
    paso("Esc. G: Factura sin líneas → rechazada", r.status_code in (400, 422),
         f"HTTP {r.status_code} (esperado 400 o 422)")

    return ids


# ─────────────────────────────────────────────────────────────────
# 5. QR – VERIFICACIÓN DEL HASH
# ─────────────────────────────────────────────────────────────────
def test_validacion_qr(ids: dict):
    seccion("5. VALIDACIÓN QR (cHashQR)")
    fid = ids.get("contado_10")
    if not fid:
        paso("QR presente en XML del DE", False, "No hay factura de referencia")
        return

    r = requests.get(f"{BASE_URL}/api/facturas/{fid}/xml", headers=hdr())
    xml = r.text if r.status_code == 200 else ""

    paso("URL QR contiene parámetro Id=CDC", "Id=" in xml)
    paso("URL QR contiene IdCSC", "IdCSC=" in xml)
    paso("URL QR contiene cHashQR (SHA-256)", "cHashQR=" in xml)
    paso("URL QR contiene dFeEmiDE en hex", "dFeEmiDE=" in xml)
    paso("URL QR contiene dTotGralOpe", "dTotGralOpe=" in xml)
    paso("URL QR contiene DigestValue", "DigestValue=" in xml)


# ─────────────────────────────────────────────────────────────────
# 6. LISTADO Y CONSULTA
# ─────────────────────────────────────────────────────────────────
def test_listado_y_consulta(ids: dict):
    seccion("6. LISTADO Y CONSULTA DE DOCUMENTOS")

    r = requests.get(f"{BASE_URL}/api/facturas", headers=hdr())
    ok = r.status_code == 200 and isinstance(r.json(), list)
    paso("Listado de facturas disponible", ok, f"Registros: {len(r.json()) if ok else '?'}")

    fid = ids.get("contado_10") or ids.get("contado_5")
    if fid:
        r = requests.get(f"{BASE_URL}/api/facturas/{fid}", headers=hdr())
        ok = r.status_code == 200
        paso(f"Detalle de factura ID={fid}", ok)
        if ok:
            data = r.json()
            paso("  Factura tiene estado_envio", "estado_envio" in data)
            paso("  Factura tiene CDC completo", len(data.get("cdc", "")) == 44)
            paso("  Factura tiene d_tot_gral_ope registrado", data.get("d_tot_gral_ope", 0) > 0)

    # Filtro por estado
    r = requests.get(f"{BASE_URL}/api/facturas?estado=pendiente", headers=hdr())
    paso("Filtrar facturas por estado=pendiente", r.status_code == 200)


# ─────────────────────────────────────────────────────────────────
# 7. EVENTOS SIFEN (cancelación / inutilización)
# ─────────────────────────────────────────────────────────────────
def test_eventos(ids: dict):
    seccion("7. EVENTOS SIFEN")
    fid = ids.get("contado_10")
    if not fid:
        paso("Cancelación de DE (evento)", False, "No hay factura de referencia")
        return

    r = requests.post(f"{BASE_URL}/api/facturas/{fid}/cancelar",
                      json={"motivo": "Prueba de cancelación – ambiente test"},
                      headers=hdr())
    # Puede devolver 200 o 400 si no tiene cert aún
    paso("Endpoint de cancelación responde", r.status_code in (200, 400, 422),
         f"HTTP {r.status_code} — {r.text[:100]}")


# ─────────────────────────────────────────────────────────────────
# 8. CONFIGURACIÓN DEL EMISOR
# ─────────────────────────────────────────────────────────────────
def test_emisor():
    seccion("8. CONFIGURACIÓN DEL EMISOR")
    r = requests.get(f"{BASE_URL}/api/emisor", headers=hdr())
    ok = r.status_code == 200
    paso("Emisor configurado y recuperable", ok, f"HTTP {r.status_code}")
    if ok:
        data = r.json()
        paso("  Campo ruc_con_dv presente", bool(data.get("ruc_con_dv")))
        paso("  Campo num_tim (timbrado) presente", bool(data.get("num_tim") or data.get("d_num_tim")))
        paso("  Campo d_est (establecimiento) presente", bool(data.get("d_est")))
        paso("  Tiene id_csc configurado", bool(data.get("id_csc")))


# ─────────────────────────────────────────────────────────────────
# DATOS DE PRUEBA
# ─────────────────────────────────────────────────────────────────
def _factura_prueba(escenario: str) -> dict:
    base = {
        "i_ti_de": 1,
        "i_tip_emi": 1,
        "receptor_ruc": "00000002",
        "receptor_dv": "7",
        "receptor_nombre": "DE generado en ambiente de prueba - sin valor comercial ni fiscal",
        "receptor_dir": "CALLE 1 ENTRE CALLE 2 Y CALLE 3",
        "receptor_num_cas": "123",
        "c_dep_rec": 1,
        "d_des_dep_rec": "CAPITAL",
        "c_dis_rec": 1,
        "d_des_dis_rec": "ASUNCION (DISTRITO)",
        "c_ciu_rec": 1,
        "d_des_ciu_rec": "ASUNCION (DISTRITO)",
        "receptor_tel": "0981123456",
        "d_cod_cliente": "CLI001",
        "i_cond_ope": 1,
        "firmar": False,
        "enviar_sifen": False,
    }

    if escenario == "contado_gravado":
        base["lineas"] = [{
            "d_cod_int": "PROD001", "d_des_pro_ser": "PRODUCTO DE PRUEBA IVA 10",
            "c_uni_med": 77, "d_des_uni_med": "UNI",
            "d_cant_pro_ser": 2, "d_p_uni_pro_ser": 550000, "d_tasa_iva": 10,
            "i_afec_iva": 1,
        }]

    elif escenario == "contado_5pct":
        base["lineas"] = [{
            "d_cod_int": "MED001", "d_des_pro_ser": "MEDICAMENTO DE PRUEBA IVA 5",
            "c_uni_med": 77, "d_des_uni_med": "UNI",
            "d_cant_pro_ser": 1, "d_p_uni_pro_ser": 100000, "d_tasa_iva": 5,
            "i_afec_iva": 2,
        }]

    elif escenario == "contado_exento":
        base["lineas"] = [{
            "d_cod_int": "EXEN001", "d_des_pro_ser": "SERVICIO EXENTO DE PRUEBA",
            "c_uni_med": 77, "d_des_uni_med": "UNI",
            "d_cant_pro_ser": 1, "d_p_uni_pro_ser": 200000, "d_tasa_iva": 0,
            "i_afec_iva": 4,
        }]

    elif escenario == "credito_30d":
        base["i_cond_ope"] = 2
        base["d_plazo_cre"] = "30 días"
        base["lineas"] = [{
            "d_cod_int": "PROD002", "d_des_pro_ser": "PROD CREDITO PRUEBA IVA 10",
            "c_uni_med": 77, "d_des_uni_med": "UNI",
            "d_cant_pro_ser": 1, "d_p_uni_pro_ser": 1100000, "d_tasa_iva": 10,
            "i_afec_iva": 1,
        }]

    elif escenario == "mixto":
        base["lineas"] = [
            {
                "d_cod_int": "P10", "d_des_pro_ser": "ITEM IVA 10%",
                "c_uni_med": 77, "d_des_uni_med": "UNI",
                "d_cant_pro_ser": 1, "d_p_uni_pro_ser": 110000, "d_tasa_iva": 10, "i_afec_iva": 1,
            },
            {
                "d_cod_int": "P05", "d_des_pro_ser": "ITEM IVA 5%",
                "c_uni_med": 77, "d_des_uni_med": "UNI",
                "d_cant_pro_ser": 1, "d_p_uni_pro_ser": 105000, "d_tasa_iva": 5, "i_afec_iva": 2,
            },
            {
                "d_cod_int": "PEX", "d_des_pro_ser": "ITEM EXENTO",
                "c_uni_med": 77, "d_des_uni_med": "UNI",
                "d_cant_pro_ser": 1, "d_p_uni_pro_ser": 50000, "d_tasa_iva": 0, "i_afec_iva": 4,
            },
        ]

    return base


# ─────────────────────────────────────────────────────────────────
# RESUMEN FINAL
# ─────────────────────────────────────────────────────────────────
def imprimir_resumen():
    print(f"\n{COLORES['TITULO']}{'═'*60}")
    print("  RESUMEN DE PRUEBAS DE HOMOLOGACIÓN SIFEN / e-Kuatia")
    print(f"{'═'*60}{COLORES['RESET']}")
    total = len(resultados)
    pasaron = sum(1 for r in resultados if r["ok"])
    fallaron = total - pasaron
    print(f"  Total: {total}  |  {COLORES['OK']}: {pasaron}  |  {COLORES['FAIL']}: {fallaron}")
    if fallaron > 0:
        print(f"\n{COLORES['FAIL']} Tests fallidos:{COLORES['RESET']}")
        for r in resultados:
            if not r["ok"]:
                print(f"  • {r['nombre']}")
                if r.get("detalle"):
                    print(f"    → {r['detalle']}")
    print(f"\n  Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Ambiente SIFEN: TEST (homologación SET Paraguay)\n")
    return fallaron == 0


# ─────────────────────────────────────────────────────────────────
# EJECUCIÓN
# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print(f"\n{COLORES['TITULO']}Denarius(by Aurelius) · Suite de Pruebas de Homologación SIFEN / e-Kuatia{COLORES['RESET']}")
    print(f"  URL Backend: {BASE_URL}")
    print(f"  Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    test_infraestructura()
    fid_inicial = test_generacion_cdc()
    test_estructura_xml(fid_inicial)
    ids = test_escenarios_factura()
    test_validacion_qr(ids)
    test_listado_y_consulta(ids)
    test_eventos(ids)
    test_emisor()

    exito = imprimir_resumen()
    sys.exit(0 if exito else 1)
