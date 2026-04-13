from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Producto, Usuario
from app.schemas import ProductoCreate, ProductoOut, ProductoUpdate
from app.security import get_current_user

router = APIRouter(prefix="/api/productos", tags=["productos"])

@router.get("", response_model=List[ProductoOut])
def listar_productos(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    return db.query(Producto).filter(Producto.empresa_id == usuario.empresa_id).all()

@router.get("/{sku}", response_model=ProductoOut)
def obtener_producto(
    sku: str,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    producto = db.query(Producto).filter(
        Producto.empresa_id == usuario.empresa_id,
        Producto.sku == sku
    ).first()
    if not producto:
        raise HTTPException(404, "Producto no encontrado")
    return producto

@router.post("", response_model=ProductoOut)
def crear_producto(
    body: ProductoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    # Verificar si ya existe el SKU
    existente = db.query(Producto).filter(
        Producto.empresa_id == usuario.empresa_id,
        Producto.sku == body.sku
    ).first()
    if existente:
        raise HTTPException(400, f"El SKU {body.sku} ya está registrado.")
    
    nuevo = Producto(**body.model_dump(), empresa_id=usuario.empresa_id)
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

@router.patch("/{id}", response_model=ProductoOut)
def actualizar_producto(
    id: int,
    body: ProductoUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    producto = db.query(Producto).filter(
        Producto.id == id,
        Producto.empresa_id == usuario.empresa_id
    ).first()
    if not producto:
        raise HTTPException(404, "Producto no encontrado")
    
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(producto, key, value)
    
    db.commit()
    db.refresh(producto)
    return producto

@router.delete("/{id}")
def eliminar_producto(
    id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    producto = db.query(Producto).filter(
        Producto.id == id,
        Producto.empresa_id == usuario.empresa_id
    ).first()
    if not producto:
        raise HTTPException(404, "Producto no encontrado")
    
    db.delete(producto)
    db.commit()
    return {"ok": True}
