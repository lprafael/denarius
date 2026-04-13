# Denarius(by Aurelius) - Especificaciones Tecnicas

## 1) Objetivo del sistema

Implementar una base funcional para facturacion electronica en Paraguay (SIFEN/e-Kuatia), capaz de:

- Gestionar datos del emisor.
- Crear facturas electronicas con lineas e IVA.
- Generar CDC (44 digitos) con digito verificador modulo 11.
- Emitir XML en formato `rDE` version 150.
- Exponer API para integracion y frontend web de operacion.

## 2) Arquitectura

### 2.1 Componentes

- **Backend API**: FastAPI + SQLAlchemy.
- **Persistencia**: PostgreSQL (`denarius_db`).
- **Frontend**: React + Vite + TypeScript.
- **Contenedores**: Docker + Docker Compose.
- **Autenticacion**: token Bearer por usuario.

### 2.2 Estructura de carpetas

- `backend/app/main.py`: bootstrap y rutas.
- `backend/app/models.py`: modelo de datos.
- `backend/app/schemas.py`: contratos Pydantic.
- `backend/app/routers/`: endpoints REST.
- `backend/app/sifen/`: logica de CDC, QR, totales y XML.
- `frontend/src/`: interfaz y consumo de API.

## 3) Stack tecnologico

### 3.1 Backend

- Python 3.x
- FastAPI
- SQLAlchemy 2.x
- Pydantic 2.x
- Uvicorn

### 3.2 Frontend

- React 19
- Vite 6
- TypeScript 5

## 4) Modelo de datos

### 4.1 Empresa

Tabla: `empresa`

Campos relevantes:

- `id`
- `nombre`
- `estado`
- `created_at`

Relaciones:

- 1 empresa -> N usuarios
- 1 empresa -> 1 emisor
- 1 empresa -> N facturas

### 4.2 Usuario

Tabla: `usuario`

Campos relevantes:

- `empresa_id`
- `email`
- `password_hash`
- `salt`
- `rol`
- `activo`
- `token_actual`
- `token_expira_at`

### 4.3 Emisor

Tabla: `emisor`

Campos relevantes:

- `ruc_con_dv`
- `tipo_contribuyente`
- `razon_social`
- `num_tim`, `d_est`, `d_pun_exp`
- `ultimo_num_doc`
- `id_csc`

### 4.4 Factura

Tabla: `factura`

Campos relevantes:

- `cdc`
- `empresa_id`
- `numero_documento`
- `d_cod_seg`
- `d_fe_emi_de`
- datos de receptor
- `d_tot_gral_ope`, `d_tot_iva`
- `d_car_qr`
- `xml_generado`

### 4.5 FacturaLinea

Tabla: `factura_linea`

Campos relevantes:

- `d_cod_int`
- `d_des_pro_ser`
- `d_cant_pro_ser`
- `d_p_uni_pro_ser`
- `d_tasa_iva`
- `i_afec_iva`

## 5) Reglas de negocio implementadas

### 5.1 Numeracion de documento

- `ultimo_num_doc` se incrementa por emision.
- `numero_documento` se asigna secuencialmente.

### 5.2 CDC

Generado en `backend/app/sifen/cdc.py`.

Estructura de 44 posiciones (43 + DV):

1. Tipo de documento (`iTiDE`, 2)
2. RUC emisor (8)
3. DV emisor (1)
4. Establecimiento (3)
5. Punto expedicion (3)
6. Numero documento (7)
7. Tipo contribuyente (1)
8. Fecha emision AAAAMMDD (8)
9. Tipo emision (1)
10. Codigo seguridad (9)
11. Digito verificador modulo 11 (1)

### 5.3 IVA y totales

Implementado en `backend/app/sifen/totales.py`.

- Soporta tasas: `0`, `5`, `10`.
- Calculo de base e IVA por linea.
- Construccion de totales de `gTotSub`.

## 6) Generacion XML

Implementado en `backend/app/sifen/de_xml.py`.

### 6.1 Formato y namespace

- Nodo raiz: `rDE`
- Namespace: `http://ekuatia.set.gov.py/sifen/xsd`
- Version: `dVerFor = 150`

### 6.2 Secciones incluidas

- `DE` con `Id = CDC`
- `gOpeDE`
- `gTimb`
- `gDatGralOpe`
- `gDtipDE` (condicion, items, IVA, transporte base)
- `gTotSub`
- `Signature` (placeholder)
- `gCamFuFD` con `dCarQR`

## 7) QR y hash

Implementado en `backend/app/sifen/qr.py`.

- Construye URL con parametros de consulta.
- `cHashQR` por `sha256` sobre payload interno.
- `DigestValue` provisional hasta firma real.

## 8) API REST

### 8.1 Auth y multiempresa

- `POST /api/auth/registro-empresa`
- `POST /api/auth/login`
- `GET /api/auth/me`

Regla de aislamiento:

- Toda operacion de emision/listado se filtra por `empresa_id` del usuario autenticado.

### 8.2 Emisor

- `GET /api/emisor`: obtiene emisor actual (crea uno por defecto si no existe).
- `PUT /api/emisor`: actualiza datos del emisor.

### 8.3 Facturas

- `GET /api/facturas`: lista facturas emitidas.
- `GET /api/facturas/{id}`: detalle basico.
- `POST /api/facturas`: crea factura y genera XML.
- `GET /api/facturas/{id}/xml`: devuelve XML generado.

### 8.4 Salud

- `GET /api/health`

## 9) Seguridad y configuracion

Variables de entorno con prefijo `AURELIUS_` (se mantiene por compatibilidad técnica):

- `DATABASE_URL`
- `CORS_ORIGINS`
- `QR_BASE_URL`
- `D_VER_FOR`
- `ID_CSC_DEFAULT`
- `CSC_SECRETO`

## 10) Docker y despliegue

Archivo: `docker-compose.yml`

Servicios:

- `backend` (puerto 8000)
- `frontend` (puerto 5173)

Comando de inicio:

```bash
docker compose up --build
```

## 11) Cumplimiento normativo y estado del Sistema Denarius(by Aurelius)

### 10.1 Alineado

- Estructura XML basada en `Extructura xml_DE.xml` del proyecto.
- CDC y modulo 11 implementados.
- Separacion multiempresa por autenticacion.

### 10.2 Pendiente para produccion

- Firma digital XMLDSig real con certificado valido.
- Integracion de envio/recepcion con servicios SIFEN.
- Ajuste final de `DigestValue` y `cHashQR` conforme manual oficial vigente.
- Validaciones completas contra XSD oficial y reglas de negocio SET/DNIT.
- Matriz de cumplimiento formal requisito por requisito contra el manual tecnico vigente.

## 12) Criterios de evolucion sugeridos

1. Migrar de SQLite a PostgreSQL.
2. Incorporar migraciones de base de datos (Alembic).
3. Agregar autenticacion y perfiles de usuario.
4. Implementar auditoria de eventos y trazabilidad legal.
5. Integrar cola de reintentos para envio SIFEN.

