from __future__ import annotations

import random
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse, Response
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Certificado, Emisor, EstadoEnvioDE, Factura, FacturaLinea, EventoDE, Usuario, Producto
from app.routers.emisor import _get_or_create_emisor
from app.schemas import FacturaCreate, FacturaDetalle, FacturaOut
from app.security import get_current_user, registrar_audit
from app.sifen.cdc import generar_cdc
from app.sifen.de_xml import construir_xml_rde
from app.sifen.qr import construir_d_car_qr, digest_placeholder_para_qr
from app.sifen.sifen_client import consultar_ruc_set
from app.sifen.totales import LineaCalculo, calcular_totales_lineas
from app.sifen.xsd_validator import validar_xml_contra_xsd

router = APIRouter(prefix="/api/facturas", tags=["facturas"])


def _get_ip(request: Request) -> str:
    return request.client.host if request.client else ""


@router.get("", response_model=list[FacturaOut])
def listar(
    skip: int = 0,
    limit: int = 100,
    estado: str | None = None,
    empresa_id: int | None = None,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    if usuario.rol == "superadmin":
        q = db.query(Factura)
        if empresa_id:
            q = q.filter(Factura.empresa_id == empresa_id)
    else:
        q = db.query(Factura).filter(Factura.empresa_id == usuario.empresa_id)
        
    if estado:
        q = q.filter(Factura.estado_envio == estado)
    return q.order_by(Factura.id.desc()).offset(skip).limit(limit).all()



@router.get("/{factura_id}", response_model=FacturaDetalle)
def obtener(
    factura_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    q = db.query(Factura).filter(Factura.id == factura_id)
    if usuario.rol != "superadmin":
        q = q.filter(Factura.empresa_id == usuario.empresa_id)
    f = q.first()

    if not f:
        raise HTTPException(404, "Factura no encontrada")
    return f


@router.get("/{factura_id}/xml", response_class=PlainTextResponse)
def exportar_xml(
    factura_id: int,
    firmado: bool = False,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    q = db.query(Factura).filter(Factura.id == factura_id)
    if usuario.rol != "superadmin":
        q = q.filter(Factura.empresa_id == usuario.empresa_id)
    f = q.first()

    if not f:
        raise HTTPException(404, "Factura no encontrada")
    contenido = f.xml_firmado if firmado and f.xml_firmado else f.xml_generado
    return Response(content=contenido, media_type="application/xml")


from pydantic import BaseModel

class MotivoCancelacion(BaseModel):
    motivo: str

@router.post("/{factura_id}/cancelar")
def cancelar_factura(
    factura_id: int,
    body: MotivoCancelacion,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    f = db.query(Factura).filter(Factura.id == factura_id, Factura.empresa_id == usuario.empresa_id).first()
    if not f:
        raise HTTPException(404, "Factura no encontrada")
    if f.estado_envio == EstadoEnvioDE.aprobado:
        # Aquí debería ir lógica de generación de XML del evento de cancelación y WS
        f.cancelado = True
        f.cancelado_at = datetime.now(timezone.utc)
        f.motivo_cancelacion = body.motivo
        db.commit()
        return {"ok": True, "msg": "Factura cancelada localmente", "evento": "cancelacion"}
    elif f.estado_envio == EstadoEnvioDE.pendiente:
        # Aún no fue SIFEN, se puede invalidar localmente nomás (según Guía)
        f.estado_envio = EstadoEnvioDE.error
        f.cancelado = True
        f.cancelado_at = datetime.now(timezone.utc)
        f.motivo_cancelacion = body.motivo
        db.commit()
        return {"ok": True, "msg": "Factura invalidada localmente (no fue a SIFEN)"}
    else:
        raise HTTPException(422, "No se puede cancelar en el estado actual")



@router.post("", response_model=FacturaOut)
def crear(
    body: FacturaCreate,
    request: Request,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    emisor: Emisor = _get_or_create_emisor(db, usuario.empresa_id)
    if not body.lineas:
        raise HTTPException(400, "Debe incluir al menos una línea")
    for ln in body.lineas:
        if ln.d_tasa_iva not in (0, 5, 10):
            raise HTTPException(400, f"d_tasa_iva inválido: {ln.d_tasa_iva}. Debe ser 0, 5 o 10")

    # Numeración
    emisor.ultimo_num_doc += 1
    num_doc = emisor.ultimo_num_doc

    fe_emi = body.d_fe_emi_de or datetime.now(timezone.utc).replace(tzinfo=None)
    fecha_iso = fe_emi.date().isoformat()
    cod_seg = "".join(str(random.randint(0, 9)) for _ in range(9))

    # Cálculo de totales e IVA
    lineas_calc = [
        LineaCalculo(
            d_p_uni_pro_ser=ln.d_p_uni_pro_ser,
            d_cant_pro_ser=ln.d_cant_pro_ser,
            d_tasa_iva=ln.d_tasa_iva,
        )
        for ln in body.lineas
    ]
    detalles, tot = calcular_totales_lineas(lineas_calc)

    # Generación de CDC
    try:
        cdc = generar_cdc(
            ruc_con_dv=emisor.ruc_con_dv,
            tipo_documento=body.i_ti_de,
            establecimiento=emisor.d_est,
            punto_expedicion=emisor.d_pun_exp,
            numero_documento=num_doc,
            tipo_contribuyente=emisor.tipo_contribuyente,
            fecha_emision_iso_date=fecha_iso,
            tipo_emision=body.i_tip_emi,
            codigo_seguridad_9=cod_seg,
        )
    except ValueError as e:
        raise HTTPException(400, str(e)) from e

    # QR provisional (se actualiza tras firma si se firma)
    d_fe_str = fe_emi.strftime("%Y-%m-%dT%H:%M:%S")
    digest_hex = digest_placeholder_para_qr(cdc, d_fe_str)
    d_car_qr = construir_d_car_qr(
        cdc=cdc,
        d_fe_emi_de=d_fe_str,
        d_ruc_rec=body.receptor_ruc.zfill(8),
        d_tot_gral_ope=tot.d_tot_gral_ope,
        d_tot_iva=tot.d_tot_iva,
        c_items=len(body.lineas),
        digest_value_base64=digest_hex,
        id_csc=emisor.id_csc,
        csc_secreto=emisor.csc_secreto,
    )


    # Crear Factura en DB
    factura = Factura(
        empresa_id=usuario.empresa_id,
        emisor_id=emisor.id,
        cdc=cdc,
        numero_documento=num_doc,
        d_cod_seg=cod_seg,
        d_fe_emi_de=fe_emi,
        i_tip_emi=body.i_tip_emi,
        i_ti_de=body.i_ti_de,
        receptor_ruc=body.receptor_ruc,
        receptor_dv=body.receptor_dv,
        receptor_nombre=body.receptor_nombre,
        receptor_dir=body.receptor_dir,
        receptor_num_cas=body.receptor_num_cas,
        c_dep_rec=body.c_dep_rec,
        d_des_dep_rec=body.d_des_dep_rec,
        c_dis_rec=body.c_dis_rec,
        d_des_dis_rec=body.d_des_dis_rec,
        c_ciu_rec=body.c_ciu_rec,
        d_des_ciu_rec=body.d_des_ciu_rec,
        receptor_tel=body.receptor_tel,
        d_cod_cliente=body.d_cod_cliente,
        i_cond_ope=body.i_cond_ope,
        d_plazo_cre=body.d_plazo_cre,
        d_tot_gral_ope=tot.d_tot_gral_ope,
        d_tot_iva=tot.d_tot_iva,
        d_car_qr=d_car_qr,
        estado_envio=EstadoEnvioDE.pendiente,
    )
    db.add(factura)
    db.flush()

    # Líneas
    for orden, ln in enumerate(body.lineas, start=1):
        db.add(FacturaLinea(
            factura_id=factura.id,
            producto_id=ln.producto_id,
            orden=orden,
            d_cod_int=ln.d_cod_int,
            d_des_pro_ser=ln.d_des_pro_ser,
            c_uni_med=ln.c_uni_med,
            d_des_uni_med=ln.d_des_uni_med,
            d_cant_pro_ser=ln.d_cant_pro_ser,
            d_p_uni_pro_ser=ln.d_p_uni_pro_ser,
            d_tasa_iva=ln.d_tasa_iva,
            i_afec_iva=1 if ln.d_tasa_iva in (5, 10) else 4,
        ))

    db.commit()
    db.refresh(factura)

    lineas_db = (
        db.query(FacturaLinea)
        .filter(FacturaLinea.factura_id == factura.id)
        .order_by(FacturaLinea.orden)
        .all()
    )

    # Generar XML
    xml = construir_xml_rde(
        emisor=emisor,
        factura=factura,
        lineas=lineas_db,
        detalles_iva=detalles,
        tot=tot,
    )
    factura.xml_generado = xml

    # Validación XSD
    errores_xsd = validar_xml_contra_xsd(xml)
    errores_bloqueantes = [e for e in errores_xsd if not e.startswith("ADVERTENCIA")]
    if errores_bloqueantes:
        # Revertir numeración
        emisor.ultimo_num_doc -= 1
        db.delete(factura)
        db.commit()
        raise HTTPException(422, {"detalle": "XML no válido contra XSD oficial", "errores": errores_bloqueantes})

    # --- Firma digital (opcional) ---
    if body.firmar:
        cert = db.query(Certificado).filter(
            Certificado.empresa_id == usuario.empresa_id,
            Certificado.activo == True,
        ).order_by(Certificado.id.desc()).first()
        if not cert:
            raise HTTPException(400, "No hay certificado digital activo para esta empresa. Cargue un certificado .p12 primero.")
        pwd = body.cert_password or ""
        try:
            from app.sifen.firma import firmar_xml_rde, extraer_digest_value
            xml_firmado = firmar_xml_rde(xml, cert.ruta_archivo, pwd)
            # Recalcular QR con DigestValue real
            real_digest = extraer_digest_value(xml_firmado)
            if real_digest:
                d_car_qr_real = construir_d_car_qr(
                    cdc=cdc,
                    d_fe_emi_de=d_fe_str,
                    d_ruc_rec=body.receptor_ruc.zfill(8),
                    d_tot_gral_ope=tot.d_tot_gral_ope,
                    d_tot_iva=tot.d_tot_iva,
                    c_items=len(body.lineas),
                    digest_value_base64=real_digest,
                    id_csc=emisor.id_csc,
                    csc_secreto=emisor.csc_secreto,
                )

                factura.d_car_qr = d_car_qr_real
            factura.xml_firmado = xml_firmado
            factura.estado_envio = EstadoEnvioDE.firmado
        except Exception as e:
            raise HTTPException(500, f"Error al firmar el XML: {e}") from e

    # --- Envío SIFEN (opcional, requiere previa firma) ---
    if body.enviar_sifen:
        if not factura.xml_firmado:
            raise HTTPException(400, "Debe firmar el DE antes de enviarlo a SIFEN")
        from app.sifen.sifen_client import enviar_lote_de
        cert = db.query(Certificado).filter(
            Certificado.empresa_id == usuario.empresa_id, Certificado.activo == True
        ).order_by(Certificado.id.desc()).first()
        p12_path = cert.ruta_archivo if cert else None
        resultado = enviar_lote_de(factura.xml_firmado, cdc, p12_path=p12_path)
        factura.sifen_respuesta = resultado.get("raw", "")
        factura.sifen_protocolo = resultado.get("protocolo", "")
        factura.estado_envio = EstadoEnvioDE.aprobado if resultado.get("aprobado") else EstadoEnvioDE.rechazado
        # Si se aprobó, actualizar stock
        if factura.estado_envio == EstadoEnvioDE.aprobado:
            _actualizar_stock_por_factura(db, factura)

    db.commit()
    db.refresh(factura)

    # Auditoría
    registrar_audit(
        db,
        accion="crear_factura",
        empresa_id=usuario.empresa_id,
        usuario_id=usuario.id,
        entidad="factura",
        entidad_id=str(factura.id),
        detalle=f"CDC:{cdc} Total:{tot.d_tot_gral_ope}",
        ip=_get_ip(request),
    )
    return factura


@router.post("/{factura_id}/firmar", response_model=FacturaOut)
def firmar(
    factura_id: int,
    cert_password: str = "",
    request: Request = None,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """Firma un DE ya generado con el certificado activo de la empresa."""
    from app.sifen.firma import firmar_xml_rde, extraer_digest_value

    f = db.query(Factura).filter(Factura.id == factura_id, Factura.empresa_id == usuario.empresa_id).first()
    if not f:
        raise HTTPException(404, "Factura no encontrada")
    if not f.xml_generado:
        raise HTTPException(400, "El DE no tiene XML generado")

    cert = db.query(Certificado).filter(
        Certificado.empresa_id == usuario.empresa_id, Certificado.activo == True
    ).order_by(Certificado.id.desc()).first()
    if not cert:
        raise HTTPException(400, "No hay certificado activo")

    try:
        xml_firmado = firmar_xml_rde(f.xml_generado, cert.ruta_archivo, cert_password)
        f.xml_firmado = xml_firmado
        f.estado_envio = EstadoEnvioDE.firmado
        db.commit()
        db.refresh(f)
    except Exception as e:
        raise HTTPException(500, f"Error en firma: {e}") from e

    registrar_audit(db, accion="firmar_factura", empresa_id=usuario.empresa_id, usuario_id=usuario.id,
                    entidad="factura", entidad_id=str(factura_id), ip=_get_ip(request) if request else "")
    return f


@router.post("/{factura_id}/enviar", response_model=FacturaOut)
def enviar_a_sifen(
    factura_id: int,
    cert_password: str = "",
    request: Request = None,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """Envía el DE firmado al Webservice SIFEN."""
    from app.sifen.sifen_client import enviar_lote_de

    f = db.query(Factura).filter(Factura.id == factura_id, Factura.empresa_id == usuario.empresa_id).first()
    if not f:
        raise HTTPException(404, "Factura no encontrada")
    if not f.xml_firmado:
        raise HTTPException(400, "El DE debe estar firmado antes de enviarse")

    cert = db.query(Certificado).filter(
        Certificado.empresa_id == usuario.empresa_id, Certificado.activo == True
    ).order_by(Certificado.id.desc()).first()

    resultado = enviar_lote_de(f.xml_firmado, f.cdc, p12_path=cert.ruta_archivo if cert else None)
    f.sifen_respuesta = resultado.get("raw", "")[:4000]
    f.sifen_protocolo = resultado.get("protocolo", "")
    f.estado_envio = EstadoEnvioDE.aprobado if resultado.get("aprobado") else EstadoEnvioDE.rechazado
    # Si se aprobó, actualizar stock
    if f.estado_envio == EstadoEnvioDE.aprobado:
        _actualizar_stock_por_factura(db, f)
        db.commit()

    registrar_audit(db, accion="enviar_sifen", empresa_id=usuario.empresa_id, usuario_id=usuario.id,
                    entidad="factura", entidad_id=str(factura_id),
                    detalle=f"codigo:{resultado.get('codigo')} aprobado:{resultado.get('aprobado')}",
                    ip=_get_ip(request) if request else "")
    return f


def _actualizar_stock_por_factura(db: Session, factura: Factura):
    """Descuenta la cantidad vendida del stock actual de cada producto vinculado."""
    for linea in factura.lineas:
        if linea.producto_id:
            db.query(Producto).filter(Producto.id == linea.producto_id).update({
                Producto.stock_actual: Producto.stock_actual - linea.d_cant_pro_ser
            })


@router.post("/{factura_id}/consultar-sifen", response_model=dict)
def consultar_sifen(
    factura_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """Consulta el estado actual del DE en los servidores SIFEN."""
    from app.sifen.sifen_client import consultar_estado_de

    f = db.query(Factura).filter(Factura.id == factura_id, Factura.empresa_id == usuario.empresa_id).first()
    if not f:
        raise HTTPException(404, "Factura no encontrada")

    return consultar_estado_de(f.cdc)


import base64
import os
from io import BytesIO
try:
    import qrcode
except ImportError:
    qrcode = None
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader

@router.get("/{factura_id}/kude", response_class=HTMLResponse)
def generar_kude(
    factura_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """Genera la representación gráfica (KuDE) de la factura en HTML basándose en una plantilla."""
    f = db.query(Factura).filter(Factura.id == factura_id, Factura.empresa_id == usuario.empresa_id).first()
    if not f:
        raise HTTPException(404, "Factura no encontrada")

    qr_data_uri = ""
    if qrcode and f.d_car_qr:
        # Generar QR dinámico
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(f.d_car_qr)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        qr_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
        qr_data_uri = f"data:image/png;base64,{qr_base64}"

    # Resolver plantilla según configuración de la empresa
    template_name = f.empresa.plantilla_kude if (f.empresa and getattr(f.empresa, "plantilla_kude", None)) else "kude_ticket.html"
    templates_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
    env = Environment(loader=FileSystemLoader(templates_dir))
    
    try:
        template = env.get_template(template_name)
    except Exception as e:
        raise HTTPException(500, f"Error al cargar la plantilla '{template_name}': {str(e)}")

    html = template.render(
        factura=f,
        emisor=f.emisor,
        receptor={"nombre": f.receptor_nombre, "ruc": f.receptor_ruc, "dv": f.receptor_dv, "direccion": f.receptor_dir},
        lineas=f.lineas,
        qr_image_base64=qr_data_uri
    )
    return HTMLResponse(content=html)

@router.get("/consultar-ruc/{ruc}")
def consultar_ruc(
    ruc: str,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    """
    Consulta un RUC en SIFEN mediante el certificado de la empresa del usuario.
    """
    if not usuario.empresa_id:
        raise HTTPException(400, "El usuario no tiene una empresa asignada")
    
    emisor = db.query(Emisor).filter(Emisor.empresa_id == usuario.empresa_id).first()
    if not emisor:
        raise HTTPException(400, "La empresa no tiene emisor configurado")
    
    from app.models import Certificado
    cert = db.query(Certificado).filter(Certificado.empresa_id == usuario.empresa_id, Certificado.activo == True).first()
    if not cert:
        raise HTTPException(400, "La empresa no tiene un certificado activo cargado. Por favor, cargue su certificado .p12")
    
    import os
    # El archivo está en cert.ruta_archivo según la lógica de certificados.py
    p12_abs_path = cert.ruta_archivo
    if not os.path.exists(p12_abs_path):
        raise HTTPException(400, f"Archivo certificado no encontrado en disco: {cert.alias}")
    
    # Nota: la contraseña se asume vacía o manejada por el almacén seguro. 
    # Si requiere pass, se debe proveer o usar cert.contrasena_enc
    res = consultar_ruc_set(ruc, p12_path=p12_abs_path, p12_password="")
    return res
