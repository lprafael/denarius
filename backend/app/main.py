from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import (
    auth, emisor, facturas, usuarios, certificados, eventos, 
    inutilizacion, auditoria, empresas, docs, clientes, equipos,
    productos, compras, analitica
)

# Crear tablas al inicio
Base.metadata.create_all(bind=engine)

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



@app.get("/api/health")
def health():
    return {
        "ok": True,
        "nombre": settings.app_name,
        "version": "2.0.0",
        "sifen_ambiente": settings.sifen_ambiente,
    }
