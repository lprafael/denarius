from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import (
    auth, emisor, facturas, usuarios, certificados, eventos, 
    inutilizacion, auditoria, empresas, docs, clientes, equipos,
    productos, compras, analitica, presupuestos, geo, lotes
)

# Crear tablas al inicio
Base.metadata.create_all(bind=engine)

# Migraciones automáticas seguras para PostgreSQL
from sqlalchemy import text
try:
    with engine.begin() as conn:
        if "postgresql" in str(engine.url):
            # Empresa
            conn.execute(text("ALTER TABLE empresa ALTER COLUMN logo_url TYPE TEXT;"))
            conn.execute(text("ALTER TABLE empresa ADD COLUMN IF NOT EXISTS max_equipos INTEGER DEFAULT 0;"))
            conn.execute(text("ALTER TABLE empresa ADD COLUMN IF NOT EXISTS restriccion_equipos BOOLEAN DEFAULT FALSE;"))
            conn.execute(text("ALTER TABLE empresa ADD COLUMN IF NOT EXISTS email_admin VARCHAR(255) DEFAULT '';"))
            conn.execute(text("ALTER TABLE empresa ADD COLUMN IF NOT EXISTS plantilla_kude VARCHAR(64) DEFAULT 'kude_ticket.html';"))
            conn.execute(text("ALTER TABLE empresa ADD COLUMN IF NOT EXISTS texto_pie_presupuesto TEXT DEFAULT '';"))
            
            # Factura
            conn.execute(text("ALTER TABLE factura ADD COLUMN IF NOT EXISTS lote_id INTEGER;"))
            conn.execute(text("ALTER TABLE factura ADD COLUMN IF NOT EXISTS cdc_asociado VARCHAR(64) DEFAULT '';"))
            conn.execute(text("ALTER TABLE factura ADD COLUMN IF NOT EXISTS tipo_doc_asociado INTEGER DEFAULT 1;"))
            conn.execute(text("ALTER TABLE factura ADD COLUMN IF NOT EXISTS motivo_emision_nc INTEGER DEFAULT 1;"))
            conn.execute(text("ALTER TABLE factura ADD COLUMN IF NOT EXISTS timbrado_doc_asociado VARCHAR(16) DEFAULT '';"))
            conn.execute(text("ALTER TABLE factura ADD COLUMN IF NOT EXISTS numero_doc_asociado VARCHAR(32) DEFAULT '';"))
            conn.execute(text("ALTER TABLE factura ADD COLUMN IF NOT EXISTS fecha_doc_asociado VARCHAR(16) DEFAULT '';"))
            conn.execute(text("ALTER TABLE factura ADD COLUMN IF NOT EXISTS moneda VARCHAR(8) DEFAULT 'PYG';"))
            conn.execute(text("ALTER TABLE factura ADD COLUMN IF NOT EXISTS tipo_cambio FLOAT DEFAULT 1.0;"))
            conn.execute(text("ALTER TABLE factura ADD COLUMN IF NOT EXISTS condicion_tipo_cambio INTEGER DEFAULT 1;"))
            conn.execute(text("ALTER TABLE factura ADD COLUMN IF NOT EXISTS descuento_global INTEGER DEFAULT 0;"))
            conn.execute(text("ALTER TABLE factura ADD COLUMN IF NOT EXISTS anticipo_global INTEGER DEFAULT 0;"))
            conn.execute(text("ALTER TABLE factura ADD COLUMN IF NOT EXISTS redondeo INTEGER DEFAULT 0;"))

            # FacturaLinea
            conn.execute(text("ALTER TABLE factura_linea ADD COLUMN IF NOT EXISTS d_desc_item INTEGER DEFAULT 0;"))
            conn.execute(text("ALTER TABLE factura_linea ADD COLUMN IF NOT EXISTS d_porc_des_it FLOAT DEFAULT 0.0;"))
            conn.execute(text("ALTER TABLE factura_linea ADD COLUMN IF NOT EXISTS d_inf_item VARCHAR(255) DEFAULT '';"))

            # GeoBarrio
            conn.execute(text("ALTER TABLE geo_barrio ADD COLUMN IF NOT EXISTS codigo_barrio INTEGER DEFAULT 0;"))
            conn.execute(text("ALTER TABLE geo_barrio ADD COLUMN IF NOT EXISTS ciudad_id INTEGER;"))
            conn.execute(text("ALTER TABLE geo_barrio ADD COLUMN IF NOT EXISTS distrito_id INTEGER;"))
            conn.execute(text("ALTER TABLE geo_barrio ADD COLUMN IF NOT EXISTS departamento_id INTEGER;"))
except Exception as e:
    print(f"[DB Migration Warning] {e}")

app = FastAPI(

    title=settings.app_name,
    version="2.0.0",
    description="Sistema de Facturación Electrónica SIFEN / e-Kuatia Paraguay",
    contact={"name": "Soporte Denarius", "email": "soporte@empresa.com.py"},
    license_info={"name": "Privado"},
)

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(emisor.router)
app.include_router(facturas.router)
app.include_router(usuarios.router)
app.include_router(certificados.router)
app.include_router(eventos.router)
app.include_router(inutilizacion.router)
app.include_router(auditoria.router)
app.include_router(empresas.router)
app.include_router(docs.router)
app.include_router(clientes.router)
app.include_router(equipos.router)
app.include_router(productos.router)
app.include_router(compras.router)
app.include_router(analitica.router)
app.include_router(presupuestos.router)
app.include_router(geo.router)
app.include_router(lotes.router)



@app.get("/api/health")
def health():
    return {
        "ok": True,
        "nombre": settings.app_name,
        "version": "2.0.0",
        "sifen_ambiente": settings.sifen_ambiente,
    }
