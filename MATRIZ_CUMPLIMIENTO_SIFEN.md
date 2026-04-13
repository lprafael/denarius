# Denarius(by Aurelius) - Matriz de Cumplimiento SIFEN (Estado actual)

> Esta matriz sirve para asegurar y reasegurar cumplimiento.  
> Estado: **parcial**, requiere cierre contra manual oficial vigente (PDF tecnico DNIT/SET).

## 1) Estructura de DE (XML rDE v150)

- [x] Se genera `rDE` con namespace SIFEN.
- [x] Se genera `DE` con `Id = CDC`.
- [x] Se incluyen bloques principales (`gOpeDE`, `gTimb`, `gDatGralOpe`, `gDtipDE`, `gTotSub`, `gCamFuFD`).
- [ ] Validacion automatica contra XSD oficial vigente en cada emision.

## 2) CDC y numeracion

- [x] CDC de 44 digitos.
- [x] Digito verificador modulo 11.
- [x] Numeracion secuencial por emisor (`ultimo_num_doc`).
- [ ] Politica avanzada de contingencia y secuencias paralelas por establecimiento/punto.

## 3) Impuestos y totales

- [x] IVA 10%, 5% y exento.
- [x] Totales generales (`dTotGralOpe`, `dTotIVA`, bases gravadas).
- [ ] Cobertura total de casos especiales de manual (segmentos complementarios sectoriales).

## 4) QR y trazabilidad

- [x] Generacion de `dCarQR`.
- [ ] `DigestValue` definitivo del DE firmado.
- [ ] `cHashQR` validado con formula exacta de manual vigente.

## 5) Firma digital

- [ ] Firma XMLDSig real (actual placeholder).
- [ ] Integracion con certificado productivo y politica de renovacion.

## 6) Integracion con SIFEN

- [ ] Envio oficial de DE.
- [ ] Recepcion de respuesta (aprobado/rechazado).
- [ ] Consulta de estado.
- [ ] Eventos (cancelacion, inutilizacion, etc.) completos.

## 7) Seguridad y multiempresa

- [x] Catalogo de empresas.
- [x] Login por usuario y empresa.
- [x] Aislamiento de datos por `empresa_id`.
- [ ] Endurecimiento de seguridad (refresh token, bloqueo, auditoria, MFA opcional).

## 8) Operacion y despliegue

- [x] Ejecucion local.
- [x] Ejecucion con Docker Compose.
- [ ] Pipeline CI/CD con pruebas de regresion fiscal/documental.

## 9) Cierre de cumplimiento recomendado

1. Cargar el PDF oficial vigente en el repositorio.
2. Desglosar requisitos por seccion y numeracion del manual.
3. Mapear cada requisito a evidencia tecnica (codigo, prueba, endpoint, XML firmado).
4. Marcar brechas y fecha de cierre.
5. Ejecutar homologacion en ambiente test SIFEN y registrar actas.
