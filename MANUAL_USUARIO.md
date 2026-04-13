# 📘 Manual de Usuario - Denarius(by Aurelius) Billing System
v2.1 · SIFEN v150 · Paraguay

**Denarius(by Aurelius)** es una plataforma corporativa avanzada para la gestión de Facturación Electrónica (rDE), diseñada bajo una arquitectura multi-inquilino que garantiza el aislamiento de datos y la seguridad de cada entidad emisora.

---

## 🔐 1. Niveles de Acceso y Roles

El sistema utiliza **Control de Acceso basado en Roles (RBAC)** para segmentar las funcionalidades:

### **🛡️ SuperAdmin (Gestor de Plataforma)**
*   **Perfil**: Dueño o administrador global del sistema (Denarius Team).
*   **Funciones Especiales**:
    *   **Gestión de Empresas**: Listado global, activación e inactivación de clientes.
    *   **Eliminación Crítica**: Capacidad de remover entidades y depurar la base de datos previa confirmación.
    *   **Expansión de Equipo**: Formulario dedicado para crear nuevos usuarios con perfil de SuperAdmin.
    *   **Auditoría Global**: Supervisión de todos los movimientos de la plataforma.

### **🏢 Empresa Admin (Administrador de Cliente)**
*   **Perfil**: Encargado de contabilidad o TI de la empresa cliente.
*   **Funciones**:
    *   **Configuración SET**: Carga del CSC (Código Seguridad) e ID de CSC.
    *   **Firma Digital**: Carga de certificados `.p12` para habilitar la firma de rDE.
    *   **Gestión de Operadores**: Crear usuarios para sus cajeros/vendedores.
    *   **Reportes**: Ver todas las facturas de su sucursal/empresa.

### **🛒 Operador (Cajero/Vendedor)**
*   **Perfil**: Usuario final que interactúa con el cliente.
*   **Funciones**:
    *   Emisión de Facturas Electrónicas en tiempo real.
    *   Consulta y descarga de XML y CDC de facturas emitidas por él.

---

## 🚀 2. Guía de Inicio Rápido

### **Paso 1: Acceso al Portal**
1.  Navegue a la URL del portal (Ej: `http://localhost:8081`).
2.  Ingrese su **Email Corporativo** y **Contraseña**.
3.  El sistema detectará automáticamente su rol y presentará el tablero correspondiente.

### **Paso 2: Gestión Global (Solo SuperAdmin)**
Si usted es SuperAdmin, verá una tabla con todas las empresas registradas:
*   **Inactivar**: Use este botón si la empresa tiene deudas o ha terminado contrato. Esto impedirá que sus usuarios logueen.
*   **Eliminar**: Borra permanentemente los datos (use con extrema precaución).
*   **Crear SuperAdmin**: Al final de la página encontrará el formulario para registrar colegas administradores.

### **Paso 3: Configuración (Empresa Admin)**
1.  Vaya a la sección **Configuración Técnica**.
2.  Ingrese el **CSC** proporcionado por la SET.
3.  Suba su archivo **Certificado Digital (.p12)**.

### **Paso 4: Emisión de Facturas**
1.  Ingrese el RUC del receptor y su DV.
2.  Complete el nombre y las líneas de productos.
3.  Presione **"Generar DE y CDC"**. El sistema generará el archivo firmado oficialmente.

---

## 📊 3. Gestión y Auditoría

### **Descarga de Documentos**
Todas las facturas emitidas aparecen en la tabla inferior. Puede descargar el archivo **XML** oficial alineado a los estándares de SIFEN v150 en cualquier momento haciendo clic en el enlace "XML".

---
© 2026 Denarius(by Aurelius) Billing System · Un producto de **Poliverso**.
