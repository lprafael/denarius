# Denarius(by Aurelius) - Guia de Utilizacion

## 1) Descripcion

**Denarius(by Aurelius)** es un sistema base de facturacion electronica para Paraguay (SIFEN/e-Kuatia), con:

- Backend en FastAPI (Python).
- Frontend en React + Vite.
- Emision de DE tipo Factura Electronica.
- Generacion de CDC, calculo de IVA y exportacion XML `rDE`.

## 2) Requisitos

- Python 3.11 o superior.
- Node.js 18 o superior.
- Windows PowerShell (comandos de ejemplo).

## 3) Estructura del proyecto

- `denarius/backend`: API, logica SIFEN y base de datos SQLite.
- `denarius/frontend`: interfaz web.
- `denarius/LEEME.txt`: resumen rapido de arranque.

## 4) Puesta en marcha

### 4.1 Backend

Desde `denarius/backend`:

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Verificacion:

```powershell
curl.exe -s http://127.0.0.1:8000/api/health
```

### 4.2 Frontend

Desde `denarius/frontend`:

```powershell
npm install
npm run dev
```

Abrir en navegador:

- `http://127.0.0.1:5173`

### 4.3 Levantar con Docker

Desde `denarius/`:

```powershell
docker compose up --build
```

Servicios:

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`

Para detener:

```powershell
docker compose down
```

## 5) Flujo de uso funcional

1. Levantar backend y frontend (local o Docker).
2. Registrar una empresa en la pantalla de acceso.
3. Iniciar sesion con el usuario administrador de esa empresa.
4. Cargar datos del receptor y lineas del documento.
5. Presionar **"Generar DE y CDC"**.
6. Ver el documento en la tabla de emitidos.
7. Descargar el XML con el boton **"XML"**.

## 6) Multiempresa y seguridad

- Cada empresa tiene su propio emisor.
- Cada usuario pertenece a una empresa.
- El login devuelve token Bearer.
- Todas las operaciones de emision/listado quedan aisladas por empresa autenticada.

Endpoints de autenticacion:

- `POST /api/auth/registro-empresa`
- `POST /api/auth/login`
- `GET /api/auth/me`

## 7) Configuracion del emisor

El emisor por defecto se crea automaticamente al primer uso.

Endpoint:

- `GET /api/emisor`
- `PUT /api/emisor`

Campos clave del emisor:

- `ruc_con_dv`
- `razon_social`
- `num_tim`
- `d_est`
- `d_pun_exp`
- `tipo_contribuyente`

## 8) Endpoints principales

- `GET /api/health`
- `POST /api/auth/registro-empresa`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `GET /api/emisor`
- `PUT /api/emisor`
- `GET /api/facturas`
- `POST /api/facturas`
- `GET /api/facturas/{id}/xml`

## 9) Variables de entorno (backend)

Prefijo (se mantiene por compatibilidad técnica): `AURELIUS_`

- `DATABASE_URL` (default: `sqlite:///./denarius.db`)
- `QR_BASE_URL` (default pruebas SET)
- `CSC_SECRETO` (debe cambiarse en produccion)

## 10) Buenas practicas operativas

- No usar `CSC_SECRETO` por defecto en ambientes reales.
- Restringir CORS a dominios de produccion.
- Respaldar la base SQLite o migrar a PostgreSQL.
- Registrar trazabilidad de emisiones y errores.

## 11) Cumplimiento normativo (manuales SET/DNIT)

Implementado:

- Estructura `rDE` basada en el ejemplo XML provisto.
- CDC con modulo 11.
- Totales de IVA y campos principales de factura electronica.
- Multiempresa con aislamiento de datos por empresa autenticada.

Pendiente para asegurar cumplimiento integral:

- Firma digital XMLDSig real con certificado valido.
- Integracion completa con servicios SIFEN (envio, recepcion, estados, eventos).
- Validacion XSD oficial actual y reglas de negocio completas del manual vigente.
- Matriz formal de trazabilidad requisito-a-requisito contra manuales.

## 12) Limitaciones actuales

- La firma digital XMLDSig esta en modo placeholder.
- No existe aun envio automatico al SIFEN.
- El `DigestValue` en QR es provisional hasta integrar firma oficial.

## 13) Proximo paso recomendado

Integrar:

1. Firma digital real (PKCS#12).
2. Envio y consulta al SIFEN (ambiente test y produccion).
3. Validaciones normativas completas segun manual vigente DNIT/SET.

