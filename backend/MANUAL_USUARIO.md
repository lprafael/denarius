# 📘 Guía de Usuario Oficial — Sistema de Facturación Electrónica SIFEN / e-Kuatia

**Sistema:** Denarius Facturación Electrónica Paraguay  
**Versión Técnica:** Manual Técnico SIFEN v150 · Normativa DNIT / SET  
**Actualización:** 2026 (Catálogo Geográfico Oficial Noviembre 2025 y Guía de Buenas Prácticas Octubre 2024)

---

## 📑 Tabla de Contenidos
1. [Introducción y Conceptos Clave](#1-introducción-y-conceptos-clave)
2. [Configuración Inicial de la Empresa y Certificado Digital](#2-configuración-inicial-de-la-empresa-y-certificado-digital)
3. [Emisión de Documentos Electrónicos (DE)](#3-emisión-de-documentos-electrónicos-de)
   - 3.1 [Factura Electrónica Estándar (Tipo 1)](#31-factura-electrónica-estándar-tipo-1)
   - 3.2 [Notas de Crédito y Débito con CDC Asociado (Tipos 5 y 6)](#32-notas-de-crédito-y-débito-con-cdc-asociado-tipos-5-y-6)
   - 3.3 [Autofactura Electrónica (Tipo 4)](#33-autofactura-electrónica-tipo-4)
   - 3.4 [Facturas de Exportación y Notas de Remisión (Tipos 2 y 7)](#34-facturas-de-exportación-y-notas-de-remisión-tipos-2-y-7)
4. [Catálogo Geográfico Oficial SIFEN (Noviembre 2025)](#4-catálogo-geográfico-oficial-sifen-noviembre-2025)
5. [Cálculo de Impuestos, Descuentos, Redondeo y Multidivisa](#5-cálculo-de-impuestos-descuentos-redondeo-y-multidivisa)
6. [Monitor de Lotes Asíncronos SIFEN](#6-monitor-de-lotes-asíncronos-sifen)
7. [Firma Digital, Código QR y Visualización KuDE](#7-firma-digital-código-qr-y-visualización-kude)
8. [Eventos del DE e Inutilización de Numeración](#8-eventos-del-de-e-inutilización-de-numeración)
9. [Presupuestos, Inventario y Compras](#9-presupuestos-inventario-y-compras)
10. [Preguntas Frecuentes y Solución de Errores Comunes de SIFEN](#10-preguntas-frecuentes-y-solución-de-errores-comunes-de-sifen)

---

## 1. Introducción y Conceptos Clave

El Sistema **Denarius** permite la emisión, firma, transmisión y almacenamiento legal de Documentos Electrónicos válidos ante la **Dirección Nacional de Ingresos Tributarios (DNIT / SET)** de la República del Paraguay, cumpliendo con el Sistema Integrado de Facturación Electrónica Nacional (**SIFEN / e-Kuatia**).

### Términos Fundamentales
* **DE (Documento Electrónico):** Archivo digital en formato XML que contiene la información fiscal y comercial de una operación.
* **CDC (Código de Control):** Cadena única de **44 dígitos** que identifica unívocamente a cada documento electrónico en todo el país. Se compone de: Tipo de Documento (2 dígitos), RUC emisor (8 dígitos), Dígito Verificador (1 dígito), Establecimiento (3 dígitos), Punto de Expedición (3 dígitos), Número de Documento (7 dígitos), Tipo de Contribuyente (1 dígito), Fecha de Emisión (8 dígitos AAAA-MM-DD), Tipo de Emisión (1 dígito), Código de Seguridad Aleatorio (9 dígitos) y Dígito Verificador Módulo 11 (1 dígito).
* **Firma Digital (XMLDSig RSA-SHA256):** Mecanismo criptográfico que garantiza la autenticidad e integridad del documento utilizando un certificado digital emitido por una Prestadora de Servicios de Confianza (PSC) habilitada en Paraguay.
* **CSC (Código de Seguridad del Contribuyente):** Secreto alfanumérico otorgado por la SET a través del sistema Marangatú que se utiliza para firmar el enlace del Código QR.
* **KuDE (Kuaa Documento Electrónico):** Representación gráfica (PDF / Ticket impreso) del Documento Electrónico que incluye el Código QR oficial para escaneo ciudadano.

---

## 2. Configuración Inicial de la Empresa y Certificado Digital

Antes de emitir el primer documento electrónico, se debe completar la configuración en la pestaña **Configuración (🔑)**:

### Paso 1: Datos del Emisor y Timbrado Electrónico
1. Ingrese a la pestaña **Configuración**.
2. Complete la información fiscal:
   * **RUC con DV:** Ejemplo: `80012345-6`.
   * **Razón Social y Nombre de Fantasía:** Exactamente como figura en la constancia de RUC de la DNIT.
   * **Número de Timbrado Electrónico:** Timbrado asignado por la SET para Facturador Electrónico.
   * **Establecimiento (`dEst`) y Punto de Expedición (`dPunExp`):** Ejemplo: `001` - `001`.
   * **Actividad Económica Principal (`cActEco`):** Código de 5 o 6 dígitos según clasificador de la SET.
   * **Dirección, Teléfono y Correo Electrónico Fiscal.**

### Paso 2: Código de Seguridad del Contribuyente (CSC)
1. En Marangatú, genere su **CSC** de producción o test.
2. Ingrese el **ID CSC** (ej: `1` o `0001`) y el **CSC Secreto** (cadena alfanumérica de 32 caracteres provista por la SET).
3. Haga clic en **Guardar Configuración**.

### Paso 3: Carga del Certificado Digital PKCS#12 (.p12)
1. En la sección **Certificado Digital**, suba su archivo con extensión `.p12` o `.pfx`.
2. Ingrese la contraseña asignada por su entidad certificadora (PSC).
3. El sistema verificará la validez del certificado, su fecha de expiración y el titular.

---

## 3. Emisión de Documentos Electrónicos (DE)

Para emitir un documento, diríjase a la pestaña **Emitir**.

### 3.1 Factura Electrónica Estándar (Tipo 1)
1. **Tipo de DE:** Seleccione `📄 Factura Electrónica`.
2. **Receptor / Cliente:**
   * Ingrese el **RUC** del cliente (sin DV). Al salir del campo, el sistema calculará automáticamente el DV y consultará el padrón de la SET. Si el cliente ya existe en su base local, autocompletará su razón social, teléfono y dirección.
   * Para consumidores finales sin RUC, ingrese el número de Cédula de Identidad o el RUC genérico `44444401-5`.
3. **Localidad Geográfica:** Seleccione **Departamento**, **Distrito** y **Ciudad** del catálogo oficial.
4. **Condición de Venta:** Seleccione `Contado` o `Crédito` (indicando el plazo en días).
5. **Moneda y Tipo de Cambio:** Por defecto `PYG` (Guaraní). Si selecciona `USD`, `BRL`, `ARS` o `EUR`, ingrese el tipo de cambio del día.
6. **Líneas de Detalle:**
   * Seleccione un producto del inventario o ingrese descripción libre.
   * Ingrese **Cantidad**, **Precio Unitario**, **Tasa de IVA** (10%, 5% o Exento) y **Descuento por ítem** si aplica.
   * Haga clic en `➕ Agregar Ítem` para añadir más líneas.
7. **Descuento Global y Redondeo:** Ingrese descuento global si aplica a toda la factura o redondeo oficial.
8. Haga clic en **🔐 Firmar y Emitir Factura Electrónica**.

---

### 3.2 Notas de Crédito y Débito con CDC Asociado (Tipos 5 y 6)

Las Notas de Crédito y Débito electrónicas requieren **obligatoriamente** referenciar el documento original afectado:

1. **Tipo de DE:** Seleccione `🔄 Nota de Crédito Electrónica` o `➕ Nota de Débito Electrónica`.
2. **Documento Asociado:**
   * Aparecerá automáticamente el recuadro **🔗 Documento Asociado / Referenciado**.
   * **CDC de Factura Afectada:** Ingrese el código CDC de 44 dígitos de la factura que se desea anular o acreditar.
   * **Motivo de Emisión:** Seleccione una opción oficial:
     * `1 - Devolución`
     * `2 - Descuento`
     * `3 - Bonificación`
     * `4 - Crédito Incobrable`
     * `7 - Anulación`
3. Ingrese los ítems y montos que se acreditan o debitan.
4. Haga clic en **🔐 Firmar y Emitir Nota de Crédito**.

---

### 3.3 Autofactura Electrónica (Tipo 4)
Utilizada para adquisiciones a personas físicas no contribuyentes (ej: compras de productos agropecuarios u ocasionales):
1. **Tipo de DE:** Seleccione `👤 Autofactura Electrónica`.
2. Ingrese la Cédula y datos del vendedor.
3. El sistema generará el grupo oficial `gCamAE` con la retención impositiva correspondiente.

---

### 3.4 Facturas de Exportación y Notas de Remisión (Tipos 2 y 7)
* **Factura de Exportación (Tipo 2):** Permite registrar operaciones con clientes internacionales (código de país no `PRY`, Incoterms y datos de despacho aduanero).
* **Nota de Remisión Electrónica (Tipo 7):** Registra el traslado de mercaderías con indicación de fechas de inicio y fin de traslado, vehículo, chofer y motivo de traslado.

---

## 4. Catálogo Geográfico Oficial SIFEN (Noviembre 2025)

SIFEN rechaza los documentos electrónicos si los códigos de departamento (`cDepRec`), distrito (`cDisRec`) o ciudad (`cCiuRec`) no coinciden exactamente con la tabla oficial de la DNIT (Error `0160`).

El sistema incluye los **7.750 registros oficiales**:
* **18 Departamentos** (Capital, Concepción, San Pedro, Cordillera, Guairá, Caaguazú, Caazapá, Itapúa, Misiones, Paraguarí, Alto Paraná, Central, Ñeembucú, Amambay, Canindeyú, Presidente Hayes, Boquerón, Alto Paraguay).
* **272 Distritos.**
* **6.766 Ciudades y Localidades.**
* **1.104 Barrios.**

Al seleccionar un Departamento, los desplegables de Distritos y Ciudades se filtran automáticamente en cascada garantizando el 100% de consistencia.

---

## 5. Cálculo de Impuestos, Descuentos, Redondeo y Multidivisa

El motor de cálculo de Denarius aplica las fórmulas matemáticas oficiales del Manual v150:

| Concepto | Regla de Cálculo |
| :--- | :--- |
| **Precio con IVA incluido (10%)** | $\text{Base Gravada} = \text{round}\left(\frac{\text{Precio Neto} \times 100}{110}\right)$, $\text{Liquidación IVA} = \text{Precio Neto} - \text{Base Gravada}$ |
| **Precio con IVA incluido (5%)** | $\text{Base Gravada} = \text{round}\left(\frac{\text{Precio Neto} \times 100}{105}\right)$, $\text{Liquidación IVA} = \text{Precio Neto} - \text{Base Gravada}$ |
| **Exentas / Exoneradas** | $\text{Base Gravada} = 0$, $\text{Liquidación IVA} = 0$, $\text{Subtotal Exento} = \text{Precio Neto}$ |
| **Descuentos por Ítem** | Se restan directamente del total bruto del ítem antes de liquidar IVA. |
| **Descuentos Globales** | Se prorratean proporcionalmente entre todos los ítems gravados y exentos. |
| **Redondeo SIFEN (`dRedon`)** | Ajuste en guaraníes para eliminar decimales o centavos en operaciones en efectivo. |

---

## 6. Monitor de Lotes Asíncronos SIFEN

Conforme a las **Recomendaciones de Buenas Prácticas de SIFEN (Octubre 2024)**, el envío en lote asíncrono es el método estándar para la transmisión masiva de documentos electrónicos sin riesgo de bloqueo de RUC por saturación.

### ¿Cómo funciona el envío en lote?
1. Diríjase a la pestaña **📦 Lotes SIFEN**.
2. Haga clic en **➕ Enviar Nuevo Lote**.
3. Seleccione las facturas que desea enviar (hasta un máximo de **50 documentos por lote**, todos del mismo tipo).
4. Haga clic en **Enviar DEs**.
5. El sistema:
   * Empaqueta los XMLs firmados dentro del contenedor `<rLoteDE>`.
   * Comprime el archivo en un paquete `.zip` en memoria.
   * Codifica el archivo ZIP en **Base64** y lo envía al webservice `recibe-lote.wsdl`.
   * Recibe el **Número de Protocolo de Consulta** (`dProtConsLote`).
   * El lote queda en estado **ENCOLADO**.

### Consulta del Estado del Lote
* Por disposición de la SET, la consulta diferida debe realizarse tras un intervalo **$\ge 10\text{ minutos}$**.
* En el monitor de lotes, haga clic en el botón **🔍 SIFEN**.
* Cuando el lote pasa a estado **CONCLUIDO**, el sistema actualiza automáticamente el estado individual de cada factura a **APROBADO** o **RECHAZADO**, guardando el número de protocolo de autorización correspondiente.

---

## 7. Firma Digital, Código QR y Visualización KuDE

### Código QR Oficial
Cada documento genera un enlace seguro de consulta pública con la estructura:
```
https://ekuatia.set.gov.py/consultas/qr?nId_de={CDC}&dFeEmiDE={FECHA_HEX}&dRucRec={RUC}&dTotGralOpe={TOTAL}&dTotIVA={IVA}&cItems={CANT_ITEMS}&dDigestValue={DIGEST_HEX}&IdCSC={ID_CSC}&cHashQR={HASH_SHA256}
```

### Opciones de Documento en el Sistema
En el listado de facturas, cada registro cuenta con accesos directos:
* **PDF (KuDE):** Abre la representación gráfica oficial con el logotipo de su empresa, desglose impositivo y código QR escaneable listo para imprimir o enviar al cliente.
* **XML:** Descarga el archivo XML firmado digitalmente conforme al estándar W3C XMLDSig, listo para auditorías fiscales.

---

## 8. Eventos del DE e Inutilización de Numeración

### Eventos de Documentos Electrónicos
Permiten comunicar a la SET situaciones posteriores a la aprobación del DE:
* **Cancelación (`gEvCan`):** Para anular una factura emitida con error dentro del plazo reglamentario.
* **Conformidad (`gEvConf`):** Aceptación de mercaderías o servicios recibidos.
* **Disconformidad (`gEvDisconf`):** Rechazo de la factura por parte del receptor.
* **Desconocimiento (`gEvDesc`):** Declaración de no haber realizado la transacción.

### Inutilización de Numeración (`rEnviInu`)
Si por razones técnicas se salteó un rango correlativo de numeración (ej: del número 10 al 15), el administrador puede solicitar la **Inutilización de Rango** indicando el motivo para mantener la correlatividad fiscal ante la DNIT.

---

## 9. Presupuestos, Inventario y Compras

### Presupuestos con Conversión Directa
* Permite crear cotizaciones y presupuestos comerciales con validez y pie de página personalizado.
* Al ser aprobado por el cliente, presione **⚡ Facturar Presupuesto** para transferir todos los ítems, precios y datos del cliente directamente a la pantalla de emisión sin reingresar datos.

### Control de Inventario y Stock
* Cada emisión de factura o nota de remisión actualiza automáticamente las existencias de productos en el almacén.
* Soporte para SKU, código de barras, precio de costo y precio de venta.

### Registro de Compras Electrónicas
* Permite cargar los CDCs de las facturas electrónicas de proveedores para calcular automáticamente la **Proyección de IVA** (Crédito Fiscal vs. Débito Fiscal).

---

## 10. Preguntas Frecuentes y Solución de Errores Comunes de SIFEN

| Código / Error | Causa | Solución en Denarius |
| :--- | :--- | :--- |
| **0160 - Código de ciudad no coincide** | Código de departamento, distrito o ciudad no coincide con la base oficial. | Utilice los selectores en cascada oficiales actualizados a Noviembre 2025. |
| **0100 - Firma Digital no válida** | Certificado digital revocado, expirado o contraseña incorrecta. | Renueve su certificado `.p12` en Configuración y verifique la fecha de expiración. |
| **0301 - Lote no encolado** | Se mezclaron diferentes tipos de documentos en un mismo lote o el archivo ZIP superó 1 MB. | El monitor de lotes valida automáticamente que todos los documentos sean del mismo tipo y no superen 50 unidades. |
| **0361 - Lote en procesamiento** | SIFEN aún no concluyó la validación masiva. | Espere al menos 10 minutos antes de volver a presionar **🔍 SIFEN**. |
| **Error de Conexión / Timeout** | Caída temporal de los servidores de la DNIT. | El sistema almacena el documento de forma segura para retransmitirlo apenas se restablezca el servicio. |

---

*Para soporte técnico y consultas adicionales, comuníquese con el administrador del sistema.*
