# Protocolo de Seguridad: Sistema Denarius(by Aurelius) (Facturación SIFEN)

Este documento describe las medidas de seguridad técnicas y organizativas implementadas en el backend de Denarius(by Aurelius) para garantizar la integridad, confidencialidad y el cumplimiento normativo exigido por la SET/DNIT.

## 1. Aislamiento Multiempresa (Tenancy Isolation)
El sistema utiliza una arquitectura de **Base de Datos Única con Aislamiento Lógico**.
*   **Filtrado por ID**: Cada registro en las tablas críticas (`factura`, `emisor`, `certificado`, `evento_de`) está vinculado a una `empresa_id`.
*   **Seguridad en el Token**: El `empresa_id` se extrae directamente del token JWT firmado por el servidor. Ningún usuario puede consultar datos de otra empresa, incluso si conoce el ID del registro.

## 2. Gestión de Identidad y Acceso (RBAC)
Se implementan tres niveles de jerarquía:
1.  **SUPERADMIN**: Control global de la infraestructura, creación de empresas y auditoría general.
2.  **EMPRESA_ADMIN**: Administrador del cliente. Configura certificados p12, CSC y gestiona sus operarios.
3.  **OPERADOR**: Perfil restringido únicamente a la emisión de documentos y consulta de reportes propios.

## 3. Seguridad de las Credenciales
*   **Hashing**: Las contraseñas se procesan con el algoritmo **Bcrypt** (coste 12), garantizando que nunca se almacenen en texto plano.
*   **JWT (JSON Web Tokens)**:
    *   **Access Token**: Corta duración (60 min) para minimizar riesgos.
    *   **Refresh Token**: Almacenado de forma segura en la base de datos para permitir sesiones prolongadas sin re-autenticación constante, con capacidad de revocación inmediata (Logout).

## 4. Protección contra Fuerza Bruta
*   **Bloqueo de Cuenta**: Tras 5 intentos fallidos consecutivos de login, el sistema bloquea automáticamente el acceso del usuario durante 15 minutos (`bloqueado_hasta`).
*   **Auditoría de Errores**: Cada intento fallido se registra en los logs de seguridad para detectar patrones de ataque.

## 5. Gestión del Certificado Digital (.p12)
*   **Aislamiento de Archivos**: Los certificados no se guardan en la base de datos. Se almacenan en el sistema de archivos en carpetas privadas protegidas por el volumen de Docker.
*   **No persistencia de Contraseña**: Por defecto, el sistema **NO almacena la contraseña del certificado**. Ésta debe ser proveída por el usuario en cada sesión de firma, cumpliendo con los estándares más altos de seguridad.

## 6. Auditoría Técnica (Audit Log)
Toda acción crítica (Eliminación, Cambio de Rol, Carga de Certificado, Firma de Factura) genera un registro en la tabla `audit_log` indicando:
*   Usuario que realizó la acción.
*   Empresa afectada.
*   Dirección IP y Timestamp.
*   Descripción detallada del cambio.

## 7. Cumplimiento SIFEN
*   **Validación XSD previa**: Antes de emitir, el sistema valida el XML contra los esquemas oficiales para evitar el envío de datos corruptos a los servidores de la SET.
*   **Ambientes**: Soporte nativo de "Test" y "Producción" con aislamiento completo de URLs y certificados.
