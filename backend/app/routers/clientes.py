from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Cliente, Usuario, Base
from sqlalchemy import text
from app.schemas import ClienteCreate, ClienteOut
from app.security import get_current_user

router = APIRouter(prefix="/api/clientes", tags=["clientes"])

@router.get("", response_model=List[ClienteOut])
def listar_clientes(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    return db.query(Cliente).filter(Cliente.empresa_id == usuario.empresa_id).all()

@router.get("/{ruc}", response_model=ClienteOut)
def obtener_cliente_por_ruc(
    ruc: str,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    # n.b. ruc puede venir con o sin DV, buscamos match exacto o parcial
    cliente = db.query(Cliente).filter(
        Cliente.empresa_id == usuario.empresa_id,
        Cliente.ruc_con_dv.like(f"{ruc}%")
    ).first()
    if not cliente:
        raise HTTPException(404, "Cliente no encontrado")
    return cliente

@router.post("", response_model=ClienteOut)
def crear_o_actualizar_cliente(
    body: ClienteCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user)
):
    # Buscar si ya existe para esta empresa
    cliente = db.query(Cliente).filter(
        Cliente.empresa_id == usuario.empresa_id,
        Cliente.ruc_con_dv == body.ruc_con_dv
    ).first()

    if cliente:
        # Actualizar datos existentes
        for key, value in body.model_dump().items():
            setattr(cliente, key, value)
    else:
        # Crear nuevo
        cliente = Cliente(**body.model_dump(), empresa_id=usuario.empresa_id)
        db.add(cliente)
    
    db.commit()
    db.refresh(cliente)
    return cliente

@router.get("/geo/departamentos")
def listar_departamentos(db: Session = Depends(get_db)):
    res = db.execute(text("SELECT id, nombre FROM geo_departamento ORDER BY nombre")).fetchall()
    return [{"id": r[0], "nombre": r[1]} for r in res]

@router.get("/geo/distritos/{dpto_id}")
def listar_distritos(dpto_id: int, db: Session = Depends(get_db)):
    res = db.execute(text("SELECT id, nombre FROM geo_distrito WHERE departamento_id = :d_id ORDER BY nombre"), {"d_id": dpto_id}).fetchall()
    return [{"id": r[0], "nombre": r[1]} for r in res]

@router.get("/geo/barrios/{dpto_id}/{dist_id}")
def listar_barrios(dpto_id: int, dist_id: int, db: Session = Depends(get_db)):
    res = db.execute(text("SELECT id, nombre FROM geo_barrio WHERE departamento_id = :dep_id AND distrito_id = :dist_id ORDER BY nombre"), {"dep_id": dpto_id, "dist_id": dist_id}).fetchall()
    return [{"id": r[0], "nombre": r[1]} for r in res]
