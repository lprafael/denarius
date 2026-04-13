"""
Script de Automatización para Homologación SIFEN - e-Kuatia (Paraguay)

Este script genera e inyecta al backend de Denarius(by Aurelius) los 10 lotes de prueba 
exigidos por la Guía de Pruebas de la SET para habilitar a un emisor electrónico.
Se envían a SIFEN y se captura el comprobante (Protocolo SIFEN) de aprobación.

IMPORTANTE: 
Requiere que el certificado .p12 ya esté cargado en la plataforma mediante
el endpoint /api/certificados.

Ejecución:
    python tests/homologar_set.py
"""
import sys
import time
import requests
from datetime import datetime

# ─────────────────────────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────────────────────────
BASE_URL = "http://localhost:8085"
CREDS = {
    "email": "admin@empresa.com.py",
    "password": "DenariusPrueba2026"
}
CERTS_PWD = "" # Opcional: proveer esto si se usa /api/facturas con cert_password

print("=" * 60)
print("  MOTOR DE HOMOLOGACIÓN AUTOMÁTICA SIFEN / DENARIUS")
print("=" * 60)

# 1. Autenticación
print("\n1. Autenticando operador...")
r_auth = requests.post(f"{BASE_URL}/api/auth/login", json=CREDS)
if r_auth.status_code != 200:
    print(f"❌ Error de autenticación: {r_auth.text}")
    sys.exit(1)

token = r_auth.json().get("access_token")
headers = {"Authorization": f"Bearer {token}"}
print("✅ Autenticado exitosamente.")

# 2. Verificación de Certificado
print("\n2. Verificando certificado P12 Activo...")
r_cert = requests.get(f"{BASE_URL}/api/certificados", headers=headers)
if r_cert.status_code == 200 and len(r_cert.json()) > 0:
    cert = r_cert.json()[0]
    print(f"✅ Certificado detectado: {cert.get('alias')} (Serie: {cert.get('numero_serie')})")
else:
    print("❌ ATENCIÓN: No hay certificado digital (.p12) activo cargado.")
    print("   Por favor cargue uno mediante el portal web o vía POST /api/certificados")
    print("   Abortando homologación porque SIFEN rechazará la firma.")
    sys.exit(1)

# 3. Datos de Prueba (10 Escenarios)
escenarios = [
    # Requisitos: Aprobación de 10 casuísticas
    {"nombre": "Factura Contado - IVA 10%", "cond": 1, "iva": 10, "tipo": "B2B"},
    {"nombre": "Factura Contado - IVA 5%", "cond": 1, "iva": 5, "tipo": "B2B"},
    {"nombre": "Factura Contado - Exenta", "cond": 1, "iva": 0, "tipo": "B2B"},
    {"nombre": "Factura Crédito - 30 Días", "cond": 2, "iva": 10, "tipo": "B2B"},
    {"nombre": "Factura Mixta (IVA 10, 5, Exenta)", "cond": 1, "iva": "MIXTO", "tipo": "B2B"},
    {"nombre": "Factura Contado (Servicios)", "cond": 1, "iva": 10, "tipo": "B2B"},
    {"nombre": "Factura Contado a Consumidor (Desc: XYZ)", "cond": 1, "iva": 10, "tipo": "B2C"},
    {"nombre": "Factura Contado B2C Exento", "cond": 1, "iva": 0, "tipo": "B2C"},
    {"nombre": "Factura Crédito B2C - 15 Días", "cond": 2, "iva": 5, "tipo": "B2C"},
    {"nombre": "Factura Contado (Varios ítems)", "cond": 1, "iva": 10, "tipo": "B2B"},
]

def crear_payload(sc: dict) -> dict:
    base = {
        "i_ti_de": 1,
        "i_tip_emi": 1,
        "receptor_ruc": "80000000" if sc["tipo"] == "B2B" else "00000000",
        "receptor_dv": "4" if sc["tipo"] == "B2B" else "0",
        "receptor_nombre": "PRUEBA HOMOLOGACIÓN " + sc["tipo"],
        "receptor_dir": "CALLE TEST 123",
        "receptor_tel": "0981000000",
        "i_cond_ope": sc["cond"],
        "d_plazo_cre": "30 días" if sc["cond"] == 2 else "",
        "firmar": True,
        "enviar_sifen": True,
        "cert_password": CERTS_PWD
    }

    if sc["iva"] == "MIXTO":
        base["lineas"] = [
            {"d_cod_int": "01", "d_des_pro_ser": "Prod 10", "c_uni_med": 77, "d_cant_pro_ser": 1, "d_p_uni_pro_ser": 100000, "d_tasa_iva": 10},
            {"d_cod_int": "02", "d_des_pro_ser": "Prod 05", "c_uni_med": 77, "d_cant_pro_ser": 1, "d_p_uni_pro_ser": 50000, "d_tasa_iva": 5},
            {"d_cod_int": "03", "d_des_pro_ser": "Prod Ex", "c_uni_med": 77, "d_cant_pro_ser": 1, "d_p_uni_pro_ser": 20000, "d_tasa_iva": 0}
        ]
    else:
        base["lineas"] = [{
            "d_cod_int": "PRD-01", 
            "d_des_pro_ser": f"Producto Test IVA {sc['iva']}", 
            "c_uni_med": 77,
            "d_cant_pro_ser": 2, 
            "d_p_uni_pro_ser": 100000, 
            "d_tasa_iva": sc["iva"]
        }]
    return base

# 4. Inyectar Lotes
print("\n3. Enviando 10 lotes de prueba a SIFEN...")
resultados = []

for i, esc in enumerate(escenarios, 1):
    print(f"   Inyectando DE {i}/10 [{esc['nombre']}]...", end="", flush=True)
    payload = crear_payload(esc)
    
    r = requests.post(f"{BASE_URL}/api/facturas", json=payload, headers=headers)
    if r.status_code == 200:
        data = r.json()
        if data.get("estado_envio") == "aprobado":
            print(f" ✅ Lote APROBADO")
            resultados.append((esc['nombre'], data.get('cdc'), data.get('sifen_protocolo')))
        else:
            print(f" ❌ RECHAZADO: {data.get('sifen_respuesta')[:100]}")
    else:
        print(f" ❌ ERROR API: {r.text[:100]}")
    
    # SIFEN test server limits requests. Avoid 429 Too Many Requests.
    time.sleep(2)

# 5. Resumen
print("\n" + "=" * 60)
print("  REPORTE FINAL DE HOMOLOGACIÓN PARA MARANGATU")
print("=" * 60)
print("Aprobados de 10: ", len(resultados))
for i, r in enumerate(resultados, 1):
    print(f"\n{i}. Tipo: {r[0]}")
    print(f"   CDC:       {r[1]}")
    print(f"   Protocolo: {r[2]}")

print("\nSi obtuvo 10/10, copie estos CDC y Protocolos y peguelos en el portal")
print("de Declaraciones de Pruebas de Sistema e-Kuatia (SET / Marangatu).")
