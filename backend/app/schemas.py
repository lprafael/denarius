from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from typing import Optional


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
class EmpresaCreate(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=255)
    email_admin: str
    password_admin: Optional[str] = Field(None, min_length=8, max_length=128)

    ruc_con_dv: str = Field(..., description="Formato: 12345678-9")
    razon_social: str
    direccion: str = "SIN DIRECCION"
    telefono: str = "021000000"
    email: str = "contacto@empresa.com.py"
    google_token: Optional[str] = None



class EmpresaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str
    estado: str
    created_at: datetime
    restriccion_equipos: bool
    max_equipos: int



class LoginIn(BaseModel):
    email: str
    password: str
    device_id: Optional[str] = None



class LoginOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    empresa_id: int
    empresa_nombre: str
    usuario_email: str
    rol: str


class RefreshIn(BaseModel):
    refresh_token: str


class CambioPasswordIn(BaseModel):
    password_actual: str
    password_nuevo: str = Field(..., min_length=8)


class GoogleLoginIn(BaseModel):
    credential: str  # El ID Token enviado por Google
    device_id: Optional[str] = None



# ---------------------------------------------------------------------------
# Usuarios
# ---------------------------------------------------------------------------
class UsuarioCreate(BaseModel):
    email: str
    password: str = Field(..., min_length=8)
    nombre: str = ""
    rol: str = "operador"


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int
    email: str
    nombre: str
    rol: str
    activo: bool
    restriccion_equipo: bool
    created_at: datetime



class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = None
    rol: Optional[str] = None
    activo: Optional[bool] = None


# ---------------------------------------------------------------------------
# Emisor
# ---------------------------------------------------------------------------
class EmisorUpdate(BaseModel):
    ruc_con_dv: Optional[str] = None
    tipo_contribuyente: Optional[int] = None
    razon_social: Optional[str] = None
    nombre_fantasia: Optional[str] = None
    direccion: Optional[str] = None
    num_casa: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    c_dep_emi: Optional[int] = None
    d_des_dep_emi: Optional[str] = None
    c_ciu_emi: Optional[int] = None
    d_des_ciu_emi: Optional[str] = None
    c_act_eco: Optional[str] = None
    d_des_act_eco: Optional[str] = None
    c_tip_reg: Optional[int] = None
    num_tim: Optional[str] = None
    d_est: Optional[str] = None
    d_pun_exp: Optional[str] = None
    d_fe_ini_t: Optional[str] = None
    id_csc: Optional[str] = None
    csc_secreto: Optional[str] = None
    tipo_emision_habitual: Optional[int] = None



class EmisorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int
    ruc_con_dv: str
    razon_social: str
    nombre_fantasia: str
    direccion: str
    num_casa: str
    telefono: str
    email: str
    c_dep_emi: int
    d_des_dep_emi: str
    c_ciu_emi: int
    d_des_ciu_emi: str
    c_act_eco: str
    d_des_act_eco: str
    c_tip_reg: int
    num_tim: str
    d_est: str
    d_pun_exp: str
    d_fe_ini_t: str
    ultimo_num_doc: int
    id_csc: str
    csc_secreto: str



# ---------------------------------------------------------------------------
# Facturas
# ---------------------------------------------------------------------------
class LineaIn(BaseModel):
    producto_id: Optional[int] = None
    d_cod_int: str = Field(..., max_length=64)
    d_des_pro_ser: str
    d_cant_pro_ser: float = Field(gt=0)
    d_p_uni_pro_ser: int = Field(ge=0)
    d_tasa_iva: int = Field(default=10, description="5, 10 o 0 (exento)")
    c_uni_med: int = 77
    d_des_uni_med: str = "UNI"


class FacturaCreate(BaseModel):
    d_fe_emi_de: Optional[datetime] = None
    i_tip_emi: int = 1
    i_ti_de: int = 1
    receptor_ruc: str
    receptor_dv: str
    receptor_nombre: str
    receptor_dir: str = ""
    receptor_num_cas: str = "0"
    c_dep_rec: int = 1
    d_des_dep_rec: str = "CAPITAL"
    c_dis_rec: int = 1
    d_des_dis_rec: str = "ASUNCION (DISTRITO)"
    c_ciu_rec: int = 1
    d_des_ciu_rec: str = "ASUNCION (DISTRITO)"
    receptor_tel: str = ""
    d_cod_cliente: str = ""
    i_cond_ope: int = 1
    d_plazo_cre: str = ""
    lineas: list[LineaIn]
    # Control de firma y envío
    firmar: bool = Field(False, description="Si True, firma el XML con el certificado activo de la empresa")
    enviar_sifen: bool = Field(False, description="Si True, envía el DE a SIFEN automáticamente post-firma")
    cert_password: Optional[str] = Field(None, description="Contraseña del certificado .p12 para firma")


class FacturaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int
    cdc: str
    numero_documento: int
    d_fe_emi_de: datetime
    receptor_nombre: str
    receptor_ruc: str
    d_tot_gral_ope: int
    d_tot_iva: int
    estado_envio: str
    sifen_protocolo: str
    cancelado: bool
    created_at: datetime


class FacturaDetalle(FacturaOut):
    d_car_qr: str
    xml_generado: str
    xml_firmado: str
    sifen_respuesta: str


# ---------------------------------------------------------------------------
# Eventos
# ---------------------------------------------------------------------------
class EventoCreate(BaseModel):
    factura_id: int
    tipo_evento: str = Field(..., description="cancel | conformidad | disconformidad | desconocimiento | nominacion")
    motivo: str = Field(..., min_length=5, max_length=255)
    cert_password: Optional[str] = None


class EventoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    factura_id: int
    tipo_evento: str
    motivo: str
    estado: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Inutilización
# ---------------------------------------------------------------------------
class InutilizacionCreate(BaseModel):
    i_ti_de: int = 1
    d_est: str
    d_pun_exp: str
    d_num_ini: int = Field(ge=1)
    d_num_fin: int
    motivo: str = Field(..., min_length=5, max_length=255)
    cert_password: Optional[str] = None


class InutilizacionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int
    i_ti_de: int
    d_est: str
    d_pun_exp: str
    d_num_ini: int
    d_num_fin: int
    motivo: str
    estado: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Certificados
# ---------------------------------------------------------------------------
class CertificadoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int
    alias: str
    numero_serie: str
    fecha_venc: Optional[datetime]
    activo: bool
    created_at: datetime


# ---------------------------------------------------------------------------
# Logs de auditoría
# ---------------------------------------------------------------------------
class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: Optional[int]
    usuario_id: Optional[int]
    accion: str
    entidad: str
    entidad_id: str
    detalle: str
    ip: str
    created_at: datetime
# ---------------------------------------------------------------------------
# Clientes
# ---------------------------------------------------------------------------
class ClienteCreate(BaseModel):
    ruc_con_dv: str
    razon_social: str
    email: Optional[str] = ""
    telefono: Optional[str] = ""
    direccion: Optional[str] = ""
    num_casa: Optional[str] = "0"
    c_dep: Optional[int] = 1
    d_des_dep: Optional[str] = "CAPITAL"
    c_dis: Optional[int] = 1
    d_des_dis: Optional[str] = "ASUNCION (DISTRITO)"
    c_ciu: Optional[int] = 1
    d_des_ciu: Optional[str] = "ASUNCION (DISTRITO)"
    barrio: Optional[str] = ""

class ClienteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int
    ruc_con_dv: str
    razon_social: str
    email: str
    telefono: str
    direccion: str
    num_casa: str
    c_dep: int
    d_des_dep: str
    c_dis: int
    d_des_dis: str
    c_ciu: int
    d_des_ciu: str
    barrio: str
    created_at: datetime

# ---------------------------------------------------------------------------
# Equipos Autorizados
# ---------------------------------------------------------------------------
class EquipoAutorizadoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    usuario_id: int
    device_id: str
    descripcion: str
    ip_registro: str
    user_agent: str
    autorizado: bool
    created_at: datetime

class EquipoAutorizadoUpdate(BaseModel):
    autorizado: bool
    descripcion: Optional[str] = None


# ---------------------------------------------------------------------------
# Productos
# ---------------------------------------------------------------------------
class ProductoCreate(BaseModel):
    sku: str = Field(..., max_length=64)
    descripcion: str = Field(..., max_length=255)
    precio_venta: int = 0
    precio_costo: int = 0
    stock_actual: float = 0.0
    stock_minimo: float = 0.0
    c_uni_med: int = 77

class ProductoUpdate(BaseModel):
    descripcion: Optional[str] = None
    precio_venta: Optional[int] = None
    precio_costo: Optional[int] = None
    stock_actual: Optional[float] = None
    stock_minimo: Optional[float] = None
    c_uni_med: Optional[int] = None

class ProductoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int
    sku: str
    descripcion: str
    precio_venta: int
    precio_costo: int
    stock_actual: float
    stock_minimo: float
    c_uni_med: int
    created_at: datetime


# ---------------------------------------------------------------------------
# Facturas Recibidas
# ---------------------------------------------------------------------------
class FacturaRecibidaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int
    cdc: str
    emisor_ruc: str
    emisor_razon_social: str
    fecha_emision: datetime
    monto_total: int
    monto_iva: int
    tipo_documento: int
    categoria: str
    procesada: bool
    created_at: datetime


# ---------------------------------------------------------------------------
# Webhooks
# ---------------------------------------------------------------------------
class WebhookCreate(BaseModel):
    url: str = Field(..., max_length=512)
    evento: str = Field(..., max_length=64)
    descripcion: Optional[str] = ""
    secreto: Optional[str] = ""

class WebhookUpdate(BaseModel):
    url: Optional[str] = None
    evento: Optional[str] = None
    descripcion: Optional[str] = None
    activo: Optional[bool] = None

class WebhookOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int
    url: str
    evento: str
    descripcion: str
    activo: bool
    created_at: datetime

