from __future__ import annotations
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
import smtplib
from email.message import EmailMessage
import base64
import os

from app.database import get_db
from app.models import Presupuesto, PresupuestoGrupo, PresupuestoConcepto, Empresa, Usuario
from app.schemas import PresupuestoCreate, PresupuestoOut, EmailEnviarIn
from app.security import get_current_user
from app.config import settings

router = APIRouter(
    prefix="/api/presupuestos",
    tags=["Presupuestos"],
    responses={401: {"description": "No autorizado"}},
)

@router.get("/", response_model=List[PresupuestoOut])
def listar_presupuestos(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    presupuestos = db.query(Presupuesto).filter(Presupuesto.empresa_id == current_user.empresa_id).order_by(Presupuesto.id.desc()).all()
    return presupuestos

@router.post("/", response_model=PresupuestoOut)
def crear_presupuesto(
    presupuesto_in: PresupuestoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    # Generar número secuencial si no se provee
    numero = presupuesto_in.numero
    if not numero:
        ultimo = db.query(func.max(Presupuesto.numero)).filter(Presupuesto.empresa_id == current_user.empresa_id).scalar()
        numero = (ultimo or 0) + 1

    nuevo_presupuesto = Presupuesto(
        empresa_id=current_user.empresa_id,
        numero=numero,
        fecha=presupuesto_in.fecha,
        validez_dias=presupuesto_in.validez_dias,
        cliente_nombre=presupuesto_in.cliente_nombre,
        cliente_email=presupuesto_in.cliente_email,
        cliente_telefono=presupuesto_in.cliente_telefono,
        cliente_direccion=presupuesto_in.cliente_direccion,
        texto_pie=presupuesto_in.texto_pie,
        estado="borrador"
    )
    
    # Initialize total amount
    total_presupuesto = 0

    if presupuesto_in.grupos:
        for grupo_in in presupuesto_in.grupos:
            nuevo_grupo = PresupuestoGrupo(
                nombre=grupo_in.nombre,
                es_suma=grupo_in.es_suma,
                orden=grupo_in.orden,
            )
            total_grupo = 0
            for concepto_in in grupo_in.conceptos:
                nuevo_concepto = PresupuestoConcepto(
                    descripcion=concepto_in.descripcion,
                    cantidad=concepto_in.cantidad,
                    precio_unitario=concepto_in.precio_unitario,
                    orden=concepto_in.orden,
                )
                nuevo_grupo.conceptos.append(nuevo_concepto)
                total_grupo += concepto_in.cantidad * concepto_in.precio_unitario
            if grupo_in.es_suma:
                total_presupuesto += total_grupo
            else:
                total_presupuesto -= total_grupo
            nuevo_presupuesto.grupos.append(nuevo_grupo)

    nuevo_presupuesto.total = total_presupuesto
    db.add(nuevo_presupuesto)
    db.commit()
    db.refresh(nuevo_presupuesto)
    
    return nuevo_presupuesto

@router.put("/{id}", response_model=PresupuestoOut)
def update_presupuesto(
    id: int,
    presupuesto_in: PresupuestoCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    presupuesto = db.query(Presupuesto).filter(
        Presupuesto.id == id,
        Presupuesto.empresa_id == current_user.empresa_id
    ).first()

    if not presupuesto:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")

    presupuesto.numero = presupuesto_in.numero or presupuesto.numero
    if presupuesto_in.fecha:
        presupuesto.fecha = presupuesto_in.fecha
    presupuesto.validez_dias = presupuesto_in.validez_dias
    presupuesto.cliente_nombre = presupuesto_in.cliente_nombre
    presupuesto.cliente_email = presupuesto_in.cliente_email
    presupuesto.cliente_telefono = presupuesto_in.cliente_telefono
    presupuesto.cliente_direccion = presupuesto_in.cliente_direccion
    presupuesto.texto_pie = presupuesto_in.texto_pie

    # Remove old groups and concepts safely through ORM
    presupuesto.grupos.clear()
    db.commit()

    total_presupuesto = 0
    if presupuesto_in.grupos:
        for grupo_in in presupuesto_in.grupos:
            nuevo_grupo = PresupuestoGrupo(
                presupuesto_id=id,
                nombre=grupo_in.nombre,
                es_suma=grupo_in.es_suma,
                orden=grupo_in.orden,
            )
            total_grupo = 0
            for concepto_in in grupo_in.conceptos:
                nuevo_concepto = PresupuestoConcepto(
                    descripcion=concepto_in.descripcion,
                    cantidad=concepto_in.cantidad,
                    precio_unitario=concepto_in.precio_unitario,
                    orden=concepto_in.orden,
                )
                nuevo_grupo.conceptos.append(nuevo_concepto)
                total_grupo += concepto_in.cantidad * concepto_in.precio_unitario
            if grupo_in.es_suma:
                total_presupuesto += total_grupo
            else:
                total_presupuesto -= total_grupo
            presupuesto.grupos.append(nuevo_grupo)

    presupuesto.total = total_presupuesto
    db.commit()
    db.refresh(presupuesto)

    return presupuesto

@router.get("/config")
def get_presupuesto_config(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Devuelve el texto pie por defecto de la empresa para los presupuestos."""
    empresa = db.query(Empresa).filter(Empresa.id == current_user.empresa_id).first()
    return {
        "texto_pie_presupuesto": empresa.texto_pie_presupuesto if empresa else ""
    }

@router.put("/config")
def update_presupuesto_config(
    body: dict,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    """Actualiza el texto pie por defecto de la empresa."""
    empresa = db.query(Empresa).filter(Empresa.id == current_user.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    if "texto_pie_presupuesto" in body:
        empresa.texto_pie_presupuesto = body["texto_pie_presupuesto"]
    db.commit()
    return {"ok": True, "texto_pie_presupuesto": empresa.texto_pie_presupuesto}

@router.get("/autocomplete/grupos")
def autocomplete_grupos(db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    # Traer nombres únicos de grupos anteriores de la empresa
    nombres = db.query(PresupuestoGrupo.nombre).join(Presupuesto).filter(
        Presupuesto.empresa_id == current_user.empresa_id
    ).distinct().all()
    return [n[0] for n in nombres if n[0]]

@router.get("/autocomplete/conceptos")
def autocomplete_conceptos(db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    # Traer descripciones y precios únicos de conceptos anteriores
    conceptos = db.query(
        PresupuestoConcepto.descripcion, 
        PresupuestoConcepto.precio_unitario
    ).join(PresupuestoGrupo).join(Presupuesto).filter(
        Presupuesto.empresa_id == current_user.empresa_id
    ).distinct(PresupuestoConcepto.descripcion).all()
    
    return [{"descripcion": c[0], "precio": c[1]} for c in conceptos if c[0]]


@router.post("/{id}/enviar")
def enviar_presupuesto(
    id: int,
    email_in: EmailEnviarIn,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    presupuesto = db.query(Presupuesto).filter(
        Presupuesto.id == id,
        Presupuesto.empresa_id == current_user.empresa_id
    ).first()
    
    if not presupuesto:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
        
    try:
        msg = EmailMessage()
        msg['Subject'] = email_in.asunto
        msg['From'] = os.getenv("SMTP_USER", "denarius.electronico@gmail.com")
        msg['To'] = email_in.destinatario
        msg.set_content(email_in.mensaje)
        
        # Adjuntar PDF
        pdf_bytes = base64.b64decode(email_in.pdf_base64)
        msg.add_attachment(pdf_bytes, maintype='application', subtype='pdf', filename=f'Presupuesto_{presupuesto.numero}.pdf')
        
        # Enviar correo
        smtp_user = os.getenv("SMTP_USER")
        smtp_pass = os.getenv("SMTP_PASSWORD")
        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", 465))
        
        if not smtp_user or not smtp_pass:
            raise Exception("Credenciales SMTP no configuradas")
            
        with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
            
        presupuesto.email_enviado = True
        presupuesto.estado = "enviado"
        db.commit()
        
        return {"ok": True, "mensaje": "Correo enviado con éxito"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al enviar correo: {str(e)}")
