# Auditoría de Cumplimiento - Sistema Denarius(by Aurelius) vs SIFEN / e-Kuatia

**Fecha de Auditoría:** Marzo 2026
**Objetivo:** Verificar el nivel de cumplimiento del sistema "Denarius(by Aurelius)" contra el set de manuales técnicos oficiales (v150 y conexos).

---

## 1. Documentos y Normativas Evaluadas
Los siguientes manuales y especificaciones técnicas provistos en la carpeta `Manuales` fueron tomados como referencia:
- `Manual Técnico Versión 150.pdf`
- `Especificación Técnica para Integración SIFEN e-Kuatia Paraguay.pdf`
- `Guia de Pruebas para e-kuatia.pdf`
- `Guía de Mejores Prácticas para la Gestión del Envío de DE.pdf`
- `Habilitación como Facturador Electrónico.pdf`
- `Generar timbrado de Facturador Electrónico.pdf`
- `Estructura_DE xsd.xml` y `Extructura xml_DE.xml`

---

## 2. Puntos de Cumplimiento (Conforme a la Norma)

Tras la revisión del código fuente del backend (`backend/app/sifen/`), se constata que Denarius(by Aurelius) **cumple con los cimientos estructurales** requeridos:

1. **Estructura del XML (rDE v150):** 
   - El archivo `de_xml.py` construye con éxito el árbol XML con los namespaces correctos y agrupa los nodos principales requeridos por el manual v150 (`gOpeDE`, `gTimb`, `gDatGralOpe`, `gDtipDE`, `gTotSub`).
   - Sigue satisfactoriamente la lógica del archivo `Extructura xml_DE.xml`.
2. **Generación del CDC (Código de Control):**
   - La formación del código de 44 posiciones cumple la estructura de la normativa (Tipo, RUC, Establecimiento, etc.).
   - El cálculo del dígito verificador utilizando **módulo 11** (`cdc.py`) está implementado correctamente acorde a la especificación técnica.
3. **Cálculos Aritméticos e IVA:**
   - La separación de bases imponibles y cálculo de IVA al 5%, 10% y exento en `totales.py` se alinea con las sumatorias que SIFEN exige validar en la recepción del DE.
4. **Código QR:**
   - El armado paramétrico del URL y la encriptación del `cHashQR` (SHA-256) en `qr.py` siguen los lineamientos del manual para la representación gráfica.

---

## 3. Brechas Críticas y No Conformidades (Faltantes)

El sistema se encuentra en una etapa de arquitectura inicial y presenta faltantes estructurales que lo invalidarían para operar en el ambiente de test o producción de SIFEN.

1. **Firma Digital XMLDSig (Crítico):**
   - **Normativa:** El Manual Técnico V150 exige que el archivo XML esté firmado digitalmente cumpliendo el estándar XMLDSig. Adicionalmente, se requiere calcular el hash criptográfico exacto del documento `DigestValue`.
   - **Estado actual:** El sistema inserta los strings hardcodeados `"PENDIENTE_FIRMA_DIGITAL"` y `"CERTIFICADO_DIGITAL_PKCS12"`. **Debe implementarse la integración con certificados reales.**
2. **Validación contra XSD Oficial:**
   - **Normativa:** Antes del envío, se debe hacer validación del esquema para evitar rechazos masivos de la API.
   - **Estado actual:** No hay validación automática en código mediante la librería `lxml` usando el archivo `Estructura_DE xsd.xml` proporcionado.
3. **Integración Web Service (Envío y Consulta):**
   - **Normativa:** La `Especificación Técnica para Integración SIFEN` define flujos SOAP/REST para enviar el Lote de DE y solicitar su estado. La `Guía de Mejores Prácticas` define también cómo manejar colas de envío.
   - **Estado actual:** El envío automático no existe; Aurelius solo emite y retorna el string XML.
4. **Gestión de Eventos y Contingencia:**
   - **Normativa:** Cancelación, Inutilización, Nominación. 
   - **Estado actual:** Ausentes.

---

## 4. Conclusión

El sistema **Denarius(by Aurelius)** tiene una excelente base funcional y matemática (los cálculos, el CDC y el XML base están ensamblados correctamente). Sin embargo, **está incompleto** en las áreas operacionales de criptografía, firma digital y telecomunicaciones con los servidores de SIFEN.

### Siguientes pasos recomendados para la Certificación:
1. Añadir capa de firma envolte (XML Signature) con un `.p12` válido.
2. Programar cliente HTTP/SOAP hacia las URLs de test detalladas en `Guia de Pruebas para e-kuatia.pdf`.
3. Implementar validador de estructura utilizando `Estructura_DE xsd.xml` previo a persistir o enviar el XML.
