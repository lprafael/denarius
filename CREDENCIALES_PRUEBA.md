# Resumen de Accesos de Prueba (Entorno Desarrollo)

Este documento contiene las credenciales iniciales para probar la plataforma Denarius(by Aurelius) Multiempresa.

| Perfil | Email | Password | Alcance |
| :--- | :--- | :--- | :--- |
| **SuperAdmin** | `admin@denarius.com.py` | `DenariusPrueba2026` | Control Total del Sistema |
| **Admin Cliente** | `admin@empresa.com.py` | `DenariusPrueba2026` | Configuración de Empresa / Certificado |
| **Operador** | `cajero@empresa.com.py` | `DenariusPrueba2026` | Emisión de Facturas y Eventos |

---

### **Instrucciones de Uso:**
1. Iniciar el servidor backend.
2. Usar el endpoint `/auth/token` para obtener el JWT.
3. El ID de la empresa para el SuperAdmin es `1`.
4. El ID de la empresa de prueba es `2`.
