# Auditoría de Cumplimiento Normativo — Denarius(by Aurelius) vs SIFEN/e‑Kuatia

**Fecha de realización de la auditoría:** 2026-03-27  
**Sistema auditado:** Denarius(by Aurelius) (workspace `FACT_ELECTRONICA/denarius`)  
**Alcance:** Revisión documental (PDFs en `FACT_ELECTRONICA/Manuales`) y revisión de código (backend `denarius/backend/app/**`).

## 1) Documentos evaluados (fuentes)

Se revisaron los siguientes archivos provistos por el usuario:

- `Manuales/Manual Técnico Versión 150.pdf`
- `Manuales/Guía de Mejores Prácticas para la Gestión del Envío de DE.pdf`
- `Manuales/Guia de Pruebas para e-kuatia.pdf`
- `Manuales/Habilitación como Facturador Electrónico.pdf`
- `Manuales/Generar timbrado de Facturador Electrónico.pdf`
- `Manuales/Listado Checksum MD5 de las versiones del Manual Tecnico.pdf`
- `Manuales/Extructura xml_DE.xml`
- `Manuales/Estructura_DE xsd.xml`
- `Manuales/Especificación Técnica para Integración SIFEN e-Kuatia Paraguay.pdf` *(documento tipo “prompt maestro”; no se considera normativo oficial, se usa como resumen orientativo)*.

## 2) Metodología

- Se identificaron requisitos normativos/técnicos recurrentes en los manuales (CDC, XML, firma, QR, SOAP/mTLS, pruebas, habilitación, timbrado).
- Se contrastó cada requisito con la implementación presente en el código de Aurelius.
- Resultado por requisito: **CUMPLE / PARCIAL / NO CUMPLE**, indicando evidencia (archivos y fragmentos relevantes).

## 3) Resultados por requisito (resumen ejecutivo)

### 3.1 CDC (Código de Control) y DV (Módulo 11)

- **Resultado**: **CUMPLE**
- **Evidencia**: `aurelius/backend/app/sifen/cdc.py` genera CDC 43 + DV y valida longitud.

### 3.2 Estructura del DE en XML `rDE` (v150)

- **Resultado**: **PARCIAL**
- **Cumple**: estructura base similar al ejemplo `Manuales/Extructura xml_DE.xml` (grupos principales).
- **Brechas**:
  - generación de etiquetas vacías (ver 3.6)
  - cobertura incompleta de campos condicionales/obligatorios por tipo de DE y escenarios (dependen del MT v150 + notas).
- **Evidencia**: `aurelius/backend/app/sifen/de_xml.py`

### 3.3 Firma digital XMLDSig (RSA-SHA256 + transforms + canonicalización)

- **Resultado**: **PARCIAL / Riesgo alto (bloqueante para certificación)**
- **Cumple**: existe módulo de firma con RSA-SHA256 y Signature enveloped.
- **Brecha crítica**: canonicalización implementada no coincide con lo exigido por guías (C14N exclusiva).
- **Evidencia**:
  - Firma: `aurelius/backend/app/sifen/firma.py`

### 3.4 SOAP 1.2 + mTLS (autenticación mutua TLS 1.2)

- **Resultado**: **NO CUMPLE (bloqueante)**
- **Brecha crítica**:
  - el cliente SOAP construye envelope SOAP 1.1, mientras las guías exigen SOAP 1.2.
  - el uso de `.p12` directamente como `cert` en httpx no asegura mTLS correcto (normalmente se requiere cert/key en PEM o configuración específica).
- **Evidencia**: `aurelius/backend/app/sifen/sifen_client.py`

### 3.5 Algoritmo del QR (`dCarQR`, `DigestValue`, `cHashQR`)

- **Resultado**: **NO CUMPLE (bloqueante)**
- **Brecha crítica**:
  - El manual/guías describen `cHashQR` sobre la cadena completa de parámetros + CSC, con SHA-256.
  - Aurelius calcula `cHashQR` con un payload reducido (`CDC + fecha_hex + IdCSC + CSC`), no con la cadena completa.
- **Evidencia**: `aurelius/backend/app/sifen/qr.py`

### 3.6 Reglas de generación del XML (sin etiquetas vacías, sin whitespace, sin prefijos)

- **Resultado**: **NO CUMPLE**
- **Brecha**:
  - Se generan etiquetas vacías (ej.: `dSerieNum` con `""`), mientras la guía de mejores prácticas recomienda no incluirlas salvo obligatorias.
- **Evidencia**: `aurelius/backend/app/sifen/de_xml.py`

### 3.7 Validación contra XSD oficial (siRecepDE_v150.xsd)

- **Resultado**: **PARCIAL**
- **Cumple**:
  - Existe validador XSD (`xsd_validator.py`) y configuración `xsd_path` en settings.
- **Brechas**:
  - El XSD provisto en `Manuales/Estructura_DE xsd.xml` no coincide con los tags del ejemplo `Extructura xml_DE.xml` ni con los nombres SIFEN reales usados por Aurelius; no puede tomarse como “XSD oficial” para validar.
  - Si no está disponible el XSD oficial configurado, el validador devuelve ADVERTENCIA y no bloquea.
- **Evidencia**: `aurelius/backend/app/sifen/xsd_validator.py`, `aurelius/backend/app/config.py`

### 3.8 Servicios web SIFEN (recepción, consulta, eventos, lotes)

- **Resultado**: **PARCIAL**
- **Cumple**: existe cliente con funciones para enviar/consultar y eventos.
- **Brechas**:
  - diferencias estructurales con lo descrito en guías (SOAP 1.2 / namespaces / lotes zip+base64 / endpoints exactos).
  - falta de evidencias de homologación por ambiente de pruebas (Guía de Pruebas).
- **Evidencia**: `aurelius/backend/app/sifen/sifen_client.py`

### 3.9 Guía de Pruebas (set de datos y escenarios mínimos)

- **Resultado**: **NO CUMPLE** *(como automatización/suite)*
- **Brechas**:
  - no hay batería automatizada de pruebas mínimas (aprobados/rechazados por tipo de DE, lotes, eventos, validación QR).
  - no se fuerza el texto obligatorio de ambiente test (leyenda “DOCUMENTO ELECTRÓNICO SIN VALOR COMERCIAL NI FISCAL - GENERADO EN AMBIENTE DE PRUEBA” en receptor/primer ítem) como criterio de suite.
- **Evidencia**: `Manuales/Guia de Pruebas para e-kuatia.pdf` (criterios), y ausencia de scripts de pruebas en Aurelius.

### 3.10 Habilitación + Timbrado (Marangatu) + obtención CSC

- **Resultado**: **PARCIAL**
- **Interpretación correcta**:
  - Son procesos administrativos fuera del sistema (Marangatu).
  - Aurelius puede almacenar/usar timbrado y CSC pero no “tramitar” habilitación.
- **Evidencia**: `Manuales/Habilitación...pdf`, `Manuales/Generar timbrado...pdf`, y campos de emisor/config.

## 4) Veredicto global

El sistema **Denarius(by Aurelius)** se encuentra **encaminado** y cumple algunos cimientos (CDC, estructura base del DE, multiempresa, seguridad de aplicación).  
Sin embargo, **NO cumple aún** en puntos **bloqueantes** para afirmar cumplimiento integral con SIFEN/e‑Kuatia según los manuales y guías evaluadas:

- **SOAP 1.2 + mTLS** (comunicación y autenticación mutua)
- **Algoritmo de QR (`cHashQR`) conforme manual**
- **Reglas de XML sin etiquetas vacías y alineación estricta**
- **Firma digital** (alineación exacta de canonicalización/transforms)
- **Ejecución de pruebas mínimas** exigidas por la Guía de Pruebas (como suite/proceso verificable)

## 5) Recomendaciones (sin ejecutar cambios en esta auditoría)

Para lograr cumplimiento “total” y trazabilidad cerrada:

1. Alinear exactamente SOAP **1.2** y mTLS con certificados válidos según MT/Guías.
2. Implementar cálculo `cHashQR` estrictamente conforme pasos del manual.
3. Ajustar generación XML para evitar etiquetas vacías/no obligatorias y minimizar whitespace.
4. Alinear firma XMLDSig (transforms + canonicalización) exactamente al estándar exigido.
5. Incorporar una suite de pruebas/homologación que siga la **Guía de Pruebas** (casos aprobados/rechazados, lotes, eventos, validación QR).

