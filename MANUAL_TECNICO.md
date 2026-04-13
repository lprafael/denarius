# 🛠️ Manual Técnico - Denarius(by Aurelius) Billing System
v1.0 · Arquitectura de Datos

Este documento describe la estructura de la base de datos de Denarius(by Aurelius), diseñada para soportar multi-inquilino (Multitenancy) mediante aislamiento por `empresa_id`.

---

## 🏗️ 1. Arquitectura de Base de Datos
El sistema utiliza una base de datos relacional (PostgreSQL en producción) con las siguientes tablas principales:

### **Tablas de Infraestructura y Acceso**

#### **1. `empresa`**
Entidad raíz del sistema. Cada cliente (empresa) tiene un registro único aquí.
*   `id`: Identificador único (PK).
*   `nombre`: Nombre comercial de la empresa.
*   `estado`: Estado operativo (`activo`, `inactivo`).
*   `created_at`: Fecha de registro inicial.

#### **2. `usuario`**
Almacena las credenciales y roles de acceso.
*   `empresa_id`: Relación con la tabla `empresa`. (Si es NULL, es SuperAdmin global).
*   `email`: Identificador de sesión.
*   `password_hash`: Contraseña cifrada con BCrypt.
*   `rol`: Perfil de acceso (`superadmin`, `empresa_admin`, `operador`).
*   `activo`: Booleano para control de acceso individual.

---

### **Tablas de Configuración Fiscal (SET)**

#### **3. `emisor`**
Contiene los datos fiscales necesarios para generar el XML de SIFEN.
*   `empresa_id`: Relación 1:1 con la empresa.
*   `ruc_con_dv`: RUC oficial del emisor.
*   `razon_social`: Nombre legal registrado en la SET.
*   `id_csc`: Identificador del código de seguridad.
*   `ultimo_num_doc`: Contador para la numeración secuencial de facturas.

#### **4. `certificado`**
Gestiona los archivos de firma digital PKCS#12.
*   `ruta_archivo`: Ubicación del archivo `.p12` en el volumen seguro.
*   `fecha_venc`: Fecha de expiración del certificado para alertas de renovación.

---

### **Tablas de Operación (Facturación)**

#### **5. `factura`**
Cabecera de los Documentos Electrónicos (DE) emitidos.
*   `cdc`: Código de Control de 44 dígitos (Único por ley).
*   `numero_documento`: Número secuencial (Establecimiento-Punto-Número).
*   `receptor_ruc`: RUC del cliente que recibe la factura.
*   `xml_firmado`: Contenido completo del XML firmado listo para SIFEN.
*   `estado_envio`: Estado del ciclo de vida del DE (`pendiente`, `aprobado`, `rechazado`).

#### **6. `factura_linea`**
Detalle de artículos por cada factura.
*   `factura_id`: Relación con la cabecera.
*   `d_des_pro_ser`: Descripción del producto/servicio.
*   `d_tasa_iva`: Tasa impositiva aplicada (10, 5, 0).

---

### **Tablas de Auditoría y Eventos**

#### **7. `audit_log`**
Registro histórico de acciones críticas.
*   `accion`: Descripción de lo que se hizo (ej: "LOGIN", "ELIMINAR_EMPRESA").
*   `ip`: Dirección desde donde se realizó la acción.

---

## 🔄 2. Relaciones Multitenancy
El aislamiento de datos se garantiza en el nivel conceptual y de base de datos:
1.  Todas las tablas operativas (`usuario`, `emisor`, `factura`, `audit_log`) poseen una clave foránea `empresa_id`.
2.  Las consultas de la API filtran automáticamente por el `empresa_id` extraído del Token JWT del usuario.
3.  **Cascadas de Eliminación**: Al eliminar una empresa, el sistema borra automáticamente todos sus emisores, usuarios, facturas y certificados asociados (`cascade="all, delete-orphan"`).

---

## ⚖️ 3. Cumplimiento Normativo (SIFEN / e-Kuatia)

El sistema Denarius(by Aurelius) ha sido auditado y adecuado para cumplir con los estándares técnicos exigidos por la DNIT (ex SET) de Paraguay, específicamente bajo el **Manual Técnico v150**.

### **Estado de Auditoría y Cumplimiento (Marzo 2026)**

| Requisito Técnico | Estado | Observaciones / Adecuación |
| :--- | :--- | :--- |
| **Generación de CDC y DV** | ✅ **Cumple** | Implementado en `cdc.py` con algoritmo Módulo 11. |
| **Algoritmo de QR (`cHashQR`)** | ✅ **Cumple** | Adecuado el 2026-03-27 para incluir el payload completo (nVersion, Id, ..., IdCSC) + CSC. |
| **Firma Digital (XMLDSig)** | ✅ **Cumple** | Alineado con **Exclusive C14N** y transforms requeridos por SIFEN (`firma.py`). |
| **Protocolo SOAP 1.2** | ✅ **Cumple** | El sistema utiliza el envelope SOAP 1.2 (`http://www.w3.org/2003/05/soap-envelope`). |
| **Autenticación mTLS** | ✅ **Cumple** | Soporte para certificados digitales en comunicación segura con endpoints SET. |
| **Estructura XML (v150)** | ✅ **Cumple** | Generación dinámica en `de_xml.py` sin etiquetas vacías opcionales, optimizando rechazos. |

### **Especificaciones Técnicas Clave**
1.  **Seguridad**: Hashing SHA-256 para `DigestValue` y `cHashQR`.
2.  **Canonicalización**: Se aplica Canonicalización Exclusiva (C14N) antes de la firma para garantizar integridad.
3.  **Ambientes**: Soporte dual para `test` (homologación) y `prod` (producción) configurable vía `sifen_ambiente`.

---
© 2026 Denarius(by Aurelius) Technical Docs · Poliverso Development Team.
