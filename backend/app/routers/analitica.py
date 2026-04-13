from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from app.database import get_db
from app.models import Factura, FacturaRecibida, Usuario, FacturaLinea, Producto, EstadoEnvioDE
from app.security import get_current_user

router = APIRouter(prefix="/api/analitica", tags=["analitica"])

@router.get("/proyeccion-iva")
def proyeccion_iva(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    """
    Calcula el balance de IVA del mes corriente.
    IVA Ventas (Débito) - IVA Compras (Crédito)
    """
    hoy = datetime.now()
    inicio_mes = hoy.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # 1. IVA Ventas (solo facturas aprobadas por SIFEN)
    iva_ventas = db.query(func.sum(Factura.d_tot_iva)).filter(
        Factura.empresa_id == usuario.empresa_id,
        Factura.cancelado == False,
        Factura.estado_envio == EstadoEnvioDE.aprobado,
        Factura.d_fe_emi_de >= inicio_mes
    ).scalar() or 0
    
    # 2. IVA Compras (Facturas Recibidas)
    iva_compras = db.query(func.sum(FacturaRecibida.monto_iva)).filter(
        FacturaRecibida.empresa_id == usuario.empresa_id,
        FacturaRecibida.fecha_emision >= inicio_mes
    ).scalar() or 0
    
    # 3. Datos del mes anterior para comparación (opcional)
    # ...
    
    return {
        "periodo": f"{inicio_mes.strftime('%Y-%m')}",
        "iva_debito_ventas": int(iva_ventas),
        "iva_credito_compras": int(iva_compras),
        "iva_estimado_pagar": max(0, int(iva_ventas - iva_compras))
    }

@router.get("/ventas-mensuales")
def estadisticas_ventas(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    """
    Ventas agrupadas por fecha para los últimos 30 días.
    """
    limite = datetime.now() - timedelta(days=30)
    
    ventas = db.query(
        func.date(Factura.d_fe_emi_de).label("fecha"),
        func.sum(Factura.d_tot_gral_ope).label("total")
    ).filter(
        Factura.empresa_id == usuario.empresa_id,
        Factura.cancelado == False,
        Factura.estado_envio == EstadoEnvioDE.aprobado,
        Factura.d_fe_emi_de >= limite
    ).group_by(func.date(Factura.d_fe_emi_de)).all()
    
    return [{"fecha": v.fecha, "monto": int(v.total)} for v in ventas]

@router.get("/productos-top")
def productos_estrella(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    """
    Top 5 productos más vendidos por cantidad.
    """
    top = db.query(
        FacturaLinea.d_des_pro_ser.label("nombre"),
        func.sum(FacturaLinea.d_cant_pro_ser).label("cantidad")
    ).join(Factura).filter(
        Factura.empresa_id == usuario.empresa_id,
        Factura.cancelado == False,
        Factura.estado_envio == EstadoEnvioDE.aprobado
    ).group_by(FacturaLinea.d_des_pro_ser).order_by(func.sum(FacturaLinea.d_cant_pro_ser).desc()).limit(5).all()
    
    return [{"nombre": t.nombre, "cantidad": t.cantidad} for t in top]
