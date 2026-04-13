from __future__ import annotations

from datetime import datetime, timezone
import enum

from sqlalchemy import (
    Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, Float, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class UsuarioRole(str, enum.Enum):
    SUPERADMIN = "superadmin"      # Administrador de la plataforma global
    EMPRESA_ADMIN = "empresa_admin" # Administrador de una empresa específica
    OPERADOR = "operador"          # Usuario que solo emite facturas


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# Empresa
# ---------------------------------------------------------------------------
class Empresa(Base):
    __tablename__ = "empresa"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(255), unique=True)
    estado: Mapped[str] = mapped_column(String(16), default="pendiente")


    plantilla_kude: Mapped[str] = mapped_column(String(255), default="kude_ticket.html")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    usuarios: Mapped[list["Usuario"]] = relationship(back_populates="empresa", cascade="all, delete-orphan")
    emisor: Mapped["Emisor"] = relationship(back_populates="empresa", uselist=False, cascade="all, delete-orphan")
    facturas: Mapped[list["Factura"]] = relationship(back_populates="empresa")
    certificados: Mapped[list["Certificado"]] = relationship(back_populates="empresa", cascade="all, delete-orphan")
    logs: Mapped[list["AuditLog"]] = relationship(back_populates="empresa", cascade="all, delete-orphan")
    clientes: Mapped[list["Cliente"]] = relationship(back_populates="empresa", cascade="all, delete-orphan")
    productos: Mapped[list["Producto"]] = relationship(back_populates="empresa", cascade="all, delete-orphan")
    facturas_recibidas: Mapped[list["FacturaRecibida"]] = relationship(back_populates="empresa", cascade="all, delete-orphan")
    webhooks: Mapped[list["Webhook"]] = relationship(back_populates="empresa", cascade="all, delete-orphan")

    # Restricción de equipos
    restriccion_equipos: Mapped[bool] = mapped_column(Boolean, default=False)
    max_equipos: Mapped[int] = mapped_column(Integer, default=0) # 0 = sin límite



# ---------------------------------------------------------------------------
# Usuario
# ---------------------------------------------------------------------------
class Usuario(Base):
    __tablename__ = "usuario"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresa.id"), index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    rol: Mapped[UsuarioRole] = mapped_column(String(32), default=UsuarioRole.OPERADOR)
    activo: Mapped[bool] = mapped_column(Boolean, default=False)

    nombre: Mapped[str] = mapped_column(String(128), default="")
    # JWT refresh tokens
    refresh_token: Mapped[str] = mapped_column(String(512), default="", index=True)
    refresh_token_expira_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Intentos fallidos de login (bloqueo temporal)
    intentos_fallidos: Mapped[int] = mapped_column(Integer, default=0)
    bloqueado_hasta: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    # Restricción de equipo por usuario
    restriccion_equipo: Mapped[bool] = mapped_column(Boolean, default=False)

    empresa: Mapped["Empresa"] = relationship(back_populates="usuarios")
    equipos: Mapped[list["EquipoAutorizado"]] = relationship(back_populates="usuario", cascade="all, delete-orphan")



# ---------------------------------------------------------------------------
# Certificado digital por empresa
# ---------------------------------------------------------------------------
class Certificado(Base):
    __tablename__ = "certificado"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresa.id"), index=True)
    alias: Mapped[str] = mapped_column(String(64), default="principal")
    # Ruta en disco (cifrada o en volumen seguro)
    ruta_archivo: Mapped[str] = mapped_column(String(512), default="")
    # Contraseña almacenada cifrada o vacía (usuario la provee en cada operación)
    contrasena_enc: Mapped[str] = mapped_column(String(512), default="")
    numero_serie: Mapped[str] = mapped_column(String(128), default="")
    fecha_venc: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    empresa: Mapped["Empresa"] = relationship(back_populates="certificados")


# ---------------------------------------------------------------------------
# Emisor
# ---------------------------------------------------------------------------
class Emisor(Base):
    __tablename__ = "emisor"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresa.id"), unique=True, index=True)
    ruc_con_dv: Mapped[str] = mapped_column(String(32), unique=True)
    tipo_contribuyente: Mapped[int] = mapped_column(Integer, default=2)
    razon_social: Mapped[str] = mapped_column(String(255))
    nombre_fantasia: Mapped[str] = mapped_column(String(255), default="")
    direccion: Mapped[str] = mapped_column(String(255))
    num_casa: Mapped[str] = mapped_column(String(16), default="0")
    telefono: Mapped[str] = mapped_column(String(32), default="")
    email: Mapped[str] = mapped_column(String(128), default="")
    c_dep_emi: Mapped[int] = mapped_column(Integer, default=1)
    d_des_dep_emi: Mapped[str] = mapped_column(String(64), default="CAPITAL")
    c_ciu_emi: Mapped[int] = mapped_column(Integer, default=1)
    d_des_ciu_emi: Mapped[str] = mapped_column(String(128), default="ASUNCION (DISTRITO)")
    c_act_eco: Mapped[str] = mapped_column(String(16), default="46510")
    d_des_act_eco: Mapped[str] = mapped_column(
        String(255), default="COMERCIO AL POR MAYOR DE EQUIPOS INFORMATICOS Y SOFTWARE"
    )
    c_tip_reg: Mapped[int] = mapped_column(Integer, default=3)
    num_tim: Mapped[str] = mapped_column(String(16), default="12345678")
    d_est: Mapped[str] = mapped_column(String(8), default="001")
    d_pun_exp: Mapped[str] = mapped_column(String(8), default="001")
    d_serie_num: Mapped[str] = mapped_column(String(2), default="")  # Serie del timbrado (opcional, ej: "AB")
    d_fe_ini_t: Mapped[str] = mapped_column(String(16), default="2019-08-13")
    ultimo_num_doc: Mapped[int] = mapped_column(Integer, default=0)
    id_csc: Mapped[str] = mapped_column(String(8), default="0001")
    csc_secreto: Mapped[str] = mapped_column(String(64), default="CAMBIAR_EN_PRODUCCION")
    # Tipo de emisión habitual (1=Normal, 2=Contingencia, etc.)

    tipo_emision_habitual: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    empresa: Mapped["Empresa"] = relationship(back_populates="emisor")


# ---------------------------------------------------------------------------
# Factura (Documento Electrónico)
# ---------------------------------------------------------------------------
class EstadoEnvioDE(str, enum.Enum):
    pendiente = "pendiente"
    firmado = "firmado"
    enviado = "enviado"
    aprobado = "aprobado"
    rechazado = "rechazado"
    error = "error"


class Factura(Base):
    __tablename__ = "factura"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresa.id"), index=True)
    emisor_id: Mapped[int] = mapped_column(ForeignKey("emisor.id"))
    cdc: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    numero_documento: Mapped[int] = mapped_column(Integer)
    d_cod_seg: Mapped[str] = mapped_column(String(16))
    d_fe_emi_de: Mapped[datetime] = mapped_column(DateTime)
    i_tip_emi: Mapped[int] = mapped_column(Integer, default=1)
    i_ti_de: Mapped[int] = mapped_column(Integer, default=1)

    # Receptor
    receptor_ruc: Mapped[str] = mapped_column(String(16))
    receptor_dv: Mapped[str] = mapped_column(String(4))
    receptor_nombre: Mapped[str] = mapped_column(String(255))
    receptor_dir: Mapped[str] = mapped_column(String(255), default="")
    receptor_num_cas: Mapped[str] = mapped_column(String(16), default="0")
    c_dep_rec: Mapped[int] = mapped_column(Integer, default=1)
    d_des_dep_rec: Mapped[str] = mapped_column(String(64), default="CAPITAL")
    c_dis_rec: Mapped[int] = mapped_column(Integer, default=1)
    d_des_dis_rec: Mapped[str] = mapped_column(String(128), default="ASUNCION (DISTRITO)")
    c_ciu_rec: Mapped[int] = mapped_column(Integer, default=1)
    d_des_ciu_rec: Mapped[str] = mapped_column(String(128), default="ASUNCION (DISTRITO)")
    receptor_tel: Mapped[str] = mapped_column(String(32), default="")
    d_cod_cliente: Mapped[str] = mapped_column(String(32), default="")
    i_cond_ope: Mapped[int] = mapped_column(Integer, default=1)
    d_plazo_cre: Mapped[str] = mapped_column(String(16), default="")

    # Totales
    d_tot_gral_ope: Mapped[int] = mapped_column(Integer)
    d_tot_iva: Mapped[int] = mapped_column(Integer)

    # XML y QR
    d_car_qr: Mapped[str] = mapped_column(Text, default="")
    xml_generado: Mapped[str] = mapped_column(Text, default="")
    xml_firmado: Mapped[str] = mapped_column(Text, default="")

    # Estado SIFEN
    estado_envio: Mapped[str] = mapped_column(String(32), default=EstadoEnvioDE.pendiente)
    sifen_respuesta: Mapped[str] = mapped_column(Text, default="")
    sifen_protocolo: Mapped[str] = mapped_column(String(64), default="")

    # Cancelación / estado del DE
    cancelado: Mapped[bool] = mapped_column(Boolean, default=False)
    cancelado_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    motivo_cancelacion: Mapped[str] = mapped_column(String(255), default="")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    empresa: Mapped["Empresa"] = relationship(back_populates="facturas")
    emisor: Mapped["Emisor"] = relationship(backref="facturas")
    lineas: Mapped[list["FacturaLinea"]] = relationship(back_populates="factura", cascade="all, delete-orphan")
    eventos: Mapped[list["EventoDE"]] = relationship(back_populates="factura", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# Líneas de Factura
# ---------------------------------------------------------------------------
class FacturaLinea(Base):
    __tablename__ = "factura_linea"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    factura_id: Mapped[int] = mapped_column(ForeignKey("factura.id"))
    producto_id: Mapped[int | None] = mapped_column(ForeignKey("producto.id"), nullable=True)
    orden: Mapped[int] = mapped_column(Integer, default=1)
    d_cod_int: Mapped[str] = mapped_column(String(64))
    d_des_pro_ser: Mapped[str] = mapped_column(String(255))
    c_uni_med: Mapped[int] = mapped_column(Integer, default=77)
    d_des_uni_med: Mapped[str] = mapped_column(String(16), default="UNI")
    d_cant_pro_ser: Mapped[float] = mapped_column(Float, default=1.0)
    d_p_uni_pro_ser: Mapped[int] = mapped_column(Integer)
    d_tasa_iva: Mapped[int] = mapped_column(Integer, default=10)
    i_afec_iva: Mapped[int] = mapped_column(Integer, default=1)

    factura: Mapped["Factura"] = relationship(back_populates="lineas")
    producto: Mapped["Producto | None"] = relationship(back_populates="lineas")


# ---------------------------------------------------------------------------
# Eventos de DE (cancelación, inutilización, nominación, conformidad, etc.)
# ---------------------------------------------------------------------------
class EventoDE(Base):
    __tablename__ = "evento_de"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    factura_id: Mapped[int] = mapped_column(ForeignKey("factura.id"), index=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresa.id"), index=True)
    tipo_evento: Mapped[str] = mapped_column(String(32))  # cancel, inutiliza, nominacion, conformidad
    motivo: Mapped[str] = mapped_column(String(255), default="")
    xml_evento: Mapped[str] = mapped_column(Text, default="")
    estado: Mapped[str] = mapped_column(String(32), default="pendiente")
    sifen_respuesta: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    enviado_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    factura: Mapped["Factura"] = relationship(back_populates="eventos")


# ---------------------------------------------------------------------------
# Inutilización de rangos de numeración
# ---------------------------------------------------------------------------
class Inutilizacion(Base):
    __tablename__ = "inutilizacion"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresa.id"), index=True)
    emisor_id: Mapped[int] = mapped_column(ForeignKey("emisor.id"))
    i_ti_de: Mapped[int] = mapped_column(Integer, default=1)
    d_est: Mapped[str] = mapped_column(String(8))
    d_pun_exp: Mapped[str] = mapped_column(String(8))
    d_num_ini: Mapped[int] = mapped_column(Integer)
    d_num_fin: Mapped[int] = mapped_column(Integer)
    motivo: Mapped[str] = mapped_column(String(255), default="")
    xml_inutilizacion: Mapped[str] = mapped_column(Text, default="")
    estado: Mapped[str] = mapped_column(String(32), default="pendiente")
    sifen_respuesta: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


# ---------------------------------------------------------------------------
# Log de auditoría
# ---------------------------------------------------------------------------
class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int | None] = mapped_column(ForeignKey("empresa.id"), nullable=True, index=True)
    usuario_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    accion: Mapped[str] = mapped_column(String(64))
    entidad: Mapped[str] = mapped_column(String(64), default="")
    entidad_id: Mapped[str] = mapped_column(String(64), default="")
    detalle: Mapped[str] = mapped_column(Text, default="")
    ip: Mapped[str] = mapped_column(String(45), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    empresa: Mapped["Empresa | None"] = relationship(back_populates="logs")
# ---------------------------------------------------------------------------
# Cliente (Receptor recurrente)
# ---------------------------------------------------------------------------
class Cliente(Base):
    __tablename__ = "cliente"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresa.id"), index=True)
    ruc_con_dv: Mapped[str] = mapped_column(String(32), index=True) # Sin unique global, solo por empresa
    razon_social: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(128), default="")
    telefono: Mapped[str] = mapped_column(String(32), default="")
    direccion: Mapped[str] = mapped_column(String(255), default="")
    num_casa: Mapped[str] = mapped_column(String(16), default="0")
    
    # Datos geográficos (Codificación SIFEN)
    c_dep: Mapped[int] = mapped_column(Integer, default=1)
    d_des_dep: Mapped[str] = mapped_column(String(64), default="CAPITAL")
    c_dis: Mapped[int] = mapped_column(Integer, default=1)
    d_des_dis: Mapped[str] = mapped_column(String(128), default="ASUNCION (DISTRITO)")
    c_ciu: Mapped[int] = mapped_column(Integer, default=1)
    d_des_ciu: Mapped[str] = mapped_column(String(128), default="ASUNCION (DISTRITO)")
    barrio: Mapped[str] = mapped_column(String(128), default="")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    empresa: Mapped["Empresa"] = relationship(back_populates="clientes")
    
    __table_args__ = (UniqueConstraint('empresa_id', 'ruc_con_dv', name='_cliente_empresa_ruc_uc'),)

# ---------------------------------------------------------------------------
# Equipo Autorizado
# ---------------------------------------------------------------------------
class EquipoAutorizado(Base):
    __tablename__ = "equipo_autorizado"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id"), index=True)
    device_id: Mapped[str] = mapped_column(String(255), index=True) # ID único del equipo (ej: browser fingerprint)
    descripcion: Mapped[str] = mapped_column(String(128), default="Mi Equipo")
    ip_registro: Mapped[str] = mapped_column(String(45), default="")
    user_agent: Mapped[str] = mapped_column(Text, default="")
    autorizado: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    usuario: Mapped["Usuario"] = relationship(back_populates="equipos")


# ---------------------------------------------------------------------------
# Producto (Catálogo y Stock)
# ---------------------------------------------------------------------------
class Producto(Base):
    __tablename__ = "producto"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresa.id"), index=True)
    sku: Mapped[str] = mapped_column(String(64), index=True)
    descripcion: Mapped[str] = mapped_column(String(255))
    precio_venta: Mapped[int] = mapped_column(Integer, default=0)
    precio_costo: Mapped[int] = mapped_column(Integer, default=0)
    stock_actual: Mapped[float] = mapped_column(Float, default=0.0)
    stock_minimo: Mapped[float] = mapped_column(Float, default=0.0)
    c_uni_med: Mapped[int] = mapped_column(Integer, default=77)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    empresa: Mapped["Empresa"] = relationship(back_populates="productos")
    lineas: Mapped[list["FacturaLinea"]] = relationship(back_populates="producto")

    __table_args__ = (UniqueConstraint('empresa_id', 'sku', name='_producto_empresa_sku_uc'),)


# ---------------------------------------------------------------------------
# Factura Recibida (Compras/Gastos)
# ---------------------------------------------------------------------------
class FacturaRecibida(Base):
    __tablename__ = "factura_recibida"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresa.id"), index=True)
    cdc: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    emisor_ruc: Mapped[str] = mapped_column(String(32))
    emisor_razon_social: Mapped[str] = mapped_column(String(255))
    fecha_emision: Mapped[datetime] = mapped_column(DateTime)
    monto_total: Mapped[int] = mapped_column(Integer)
    monto_iva: Mapped[int] = mapped_column(Integer)
    tipo_documento: Mapped[int] = mapped_column(Integer, default=1) # 1=Factura, etc.
    xml_received: Mapped[str] = mapped_column(Text, default="")
    
    # Clasificación (opcional para el contador)
    categoria: Mapped[str] = mapped_column(String(64), default="gastos_generales")
    procesada: Mapped[bool] = mapped_column(Boolean, default=False) # Si ya afectó stock o contabilidad

    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    empresa: Mapped["Empresa"] = relationship(back_populates="facturas_recibidas")


# ---------------------------------------------------------------------------
# Denarius Connect (by Aurelius) (Webhooks)
# ---------------------------------------------------------------------------
class Webhook(Base):
    __tablename__ = "webhook"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    empresa_id: Mapped[int] = mapped_column(ForeignKey("empresa.id"), index=True)
    url: Mapped[str] = mapped_column(String(512))
    evento: Mapped[str] = mapped_column(String(64)) # factura.emitida, factura.cancelada, etc.
    descripcion: Mapped[str] = mapped_column(String(255), default="")
    secreto: Mapped[str] = mapped_column(String(128), default="")
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    empresa: Mapped["Empresa"] = relationship(back_populates="webhooks")

