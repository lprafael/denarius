from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.models import GeoDepartamento, GeoDistrito, GeoCiudad, GeoBarrio

router = APIRouter(prefix="/api/geo", tags=["geografia"])


@router.get("/departamentos")
def listar_departamentos(db: Session = Depends(get_db)):
    """Retorna los 18 departamentos oficiales de SIFEN."""
    deps = db.query(GeoDepartamento).order_by(GeoDepartamento.id).all()
    return [{"id": d.id, "nombre": d.nombre} for d in deps]


@router.get("/distritos")
def listar_distritos(
    departamento_id: int | None = None,
    db: Session = Depends(get_db),
):
    """Retorna los distritos oficiales, filtrados por departamento."""
    q = db.query(GeoDistrito)
    if departamento_id is not None:
        q = q.filter(GeoDistrito.departamento_id == departamento_id)
    distritos = q.order_by(GeoDistrito.nombre).all()
    return [{"id": d.id, "departamento_id": d.departamento_id, "nombre": d.nombre} for d in distritos]


@router.get("/ciudades")
def listar_ciudades(
    distrito_id: int | None = None,
    departamento_id: int | None = None,
    q: str | None = None,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    """Retorna ciudades/localidades oficiales para los campos cCiu y dDesCiu."""
    query = db.query(GeoCiudad)
    if distrito_id is not None:
        query = query.filter(GeoCiudad.distrito_id == distrito_id)
    if departamento_id is not None:
        query = query.filter(GeoCiudad.departamento_id == departamento_id)
    if q:
        query = query.filter(GeoCiudad.nombre.ilike(f"%{q.strip()}%"))
    ciudades = query.order_by(GeoCiudad.nombre).limit(limit).all()
    return [
        {
            "id": c.id,
            "distrito_id": c.distrito_id,
            "departamento_id": c.departamento_id,
            "nombre": c.nombre,
        }
        for c in ciudades
    ]


@router.get("/barrios")
def listar_barrios(
    ciudad_id: int | None = None,
    distrito_id: int | None = None,
    db: Session = Depends(get_db),
):
    """Retorna barrios asociados a una ciudad o distrito."""
    query = db.query(GeoBarrio)
    if ciudad_id is not None:
        query = query.filter(GeoBarrio.ciudad_id == ciudad_id)
    elif distrito_id is not None:
        query = query.filter(GeoBarrio.distrito_id == distrito_id)
    barrios = query.order_by(GeoBarrio.nombre).all()
    return [
        {
            "id": b.id,
            "codigo_barrio": b.codigo_barrio,
            "nombre": b.nombre,
            "ciudad_id": b.ciudad_id,
            "distrito_id": b.distrito_id,
            "departamento_id": b.departamento_id,
        }
        for b in barrios
    ]


@router.get("/buscar")
def buscar_localidad(
    q: str = Query(..., min_length=2),
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """Búsqueda integral de localidad retornando departamento, distrito y ciudad."""
    ciudades = (
        db.query(GeoCiudad)
        .join(GeoDistrito, GeoCiudad.distrito_id == GeoDistrito.id)
        .join(GeoDepartamento, GeoCiudad.departamento_id == GeoDepartamento.id)
        .filter(
            or_(
                GeoCiudad.nombre.ilike(f"%{q.strip()}%"),
                GeoDistrito.nombre.ilike(f"%{q.strip()}%"),
            )
        )
        .limit(limit)
        .all()
    )
    return [
        {
            "c_dep": c.departamento_id,
            "d_des_dep": c.departamento.nombre if c.departamento else "",
            "c_dist": c.distrito_id,
            "d_des_dist": c.distrito.nombre if c.distrito else "",
            "c_ciu": c.id,
            "d_des_ciu": c.nombre,
        }
        for c in ciudades
    ]


buscar_localidades = buscar_localidad
