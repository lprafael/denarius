"""
Seeder oficial de Catálogo Geográfico SIFEN / e-Kuatia (DNIT Paraguay).
Soporta carga ultrarrápida desde geo_oficial_data.json.gz o desde el Excel oficial Noviembre 2025.
"""
from __future__ import annotations

import gzip
import json
import os
import sys
from pathlib import Path

# Añadir el backend al path para importar modelos y base de datos
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import Base, SessionLocal, engine
from app.models import GeoBarrio, GeoCiudad, GeoDepartamento, GeoDistrito

JSON_GZ_PATH = Path(__file__).resolve().parent / "geo_oficial_data.json.gz"
POSSIBLE_EXCEL_PATHS = [
    Path(__file__).resolve().parent.parent.parent / "Manuales" / "CÓDIGO DE REFERENCIA GEOGRAFICA_NOVIEMBRE_2025__.xlsx",
    Path(__file__).resolve().parent.parent.parent.parent / "Manuales" / "CÓDIGO DE REFERENCIA GEOGRAFICA_NOVIEMBRE_2025__.xlsx",
    Path("/app/xsd/CÓDIGO DE REFERENCIA GEOGRAFICA_NOVIEMBRE_2025__.xlsx"),
    Path("/app/Manuales/CÓDIGO DE REFERENCIA GEOGRAFICA_NOVIEMBRE_2025__.xlsx"),
]


from sqlalchemy import text

def seed_catalogo_geografico() -> bool:
    print("Iniciando carga del Catálogo Geográfico Oficial SIFEN (DNIT Noviembre 2025)...")
    Base.metadata.create_all(bind=engine)
    
    # Migrar columnas de geo_barrio si la tabla ya existía con esquema anterior
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE geo_barrio ADD COLUMN IF NOT EXISTS codigo_barrio INTEGER DEFAULT 0;"))
            conn.execute(text("ALTER TABLE geo_barrio ADD COLUMN IF NOT EXISTS ciudad_id INTEGER;"))
            conn.execute(text("ALTER TABLE geo_barrio ADD COLUMN IF NOT EXISTS distrito_id INTEGER;"))
            conn.execute(text("ALTER TABLE geo_barrio ADD COLUMN IF NOT EXISTS departamento_id INTEGER;"))
    except Exception as e:
        print(f"Nota de migración geo_barrio: {e}")

    db = SessionLocal()

    # Si ya existen departamentos y ciudades, omitir o verificar
    existentes = db.query(GeoCiudad).count()
    if existentes >= 6700:
        print(f"Catálogo geográfico ya se encuentra poblado en BD ({existentes} ciudades).")
        db.close()
        return True

    # 1. Intentar cargar desde JSON GZ ultrarrápido
    if JSON_GZ_PATH.exists():
        print(f"Cargando datos optimizados desde {JSON_GZ_PATH.name}...")
        try:
            with gzip.open(JSON_GZ_PATH, "rt", encoding="utf-8") as gf:
                data = json.load(gf)

            deps = data["departamentos"]
            dists = data["distritos"]
            cius = data["ciudades"]
            barrios = data["barrios"]

            # Guardar departamentos
            for dep_id_str, dep_nom in deps.items():
                dep_id = int(dep_id_str)
                if not db.query(GeoDepartamento).filter(GeoDepartamento.id == dep_id).first():
                    db.add(GeoDepartamento(id=dep_id, nombre=dep_nom))
            db.commit()

            # Guardar distritos
            for dist_id_str, dist_info in dists.items():
                dist_id = int(dist_id_str)
                if not db.query(GeoDistrito).filter(GeoDistrito.id == dist_id).first():
                    db.add(GeoDistrito(id=dist_id, departamento_id=dist_info["dep_id"], nombre=dist_info["nombre"]))
            db.commit()

            # Guardar ciudades (en lotes para alta velocidad)
            ciu_objs = []
            for ciu_id_str, ciu_info in cius.items():
                ciu_id = int(ciu_id_str)
                if not db.query(GeoCiudad).filter(GeoCiudad.id == ciu_id).first():
                    ciu_objs.append(
                        GeoCiudad(
                            id=ciu_id,
                            distrito_id=ciu_info["dist_id"],
                            departamento_id=ciu_info["dep_id"],
                            nombre=ciu_info["nombre"],
                        )
                    )
            if ciu_objs:
                db.bulk_save_objects(ciu_objs)
                db.commit()

            # Guardar barrios
            bar_objs = []
            for b in barrios:
                bar_objs.append(
                    GeoBarrio(
                        codigo_barrio=b["c_bar"],
                        nombre=b["d_bar"],
                        ciudad_id=b["ciu_id"],
                        distrito_id=b["dist_id"],
                        departamento_id=b["dep_id"],
                    )
                )
            if bar_objs:
                db.bulk_save_objects(bar_objs)
                db.commit()

            print(f"Carga completada con éxito: {len(deps)} Deptos, {len(dists)} Distritos, {len(cius)} Ciudades, {len(barrios)} Barrios.")
            return True
        except Exception as e:
            print(f"Error al cargar desde JSON GZ: {e}. Intentando desde Excel...")
            db.rollback()

    # 2. Fallback a Excel
    excel_path = None
    for p in POSSIBLE_EXCEL_PATHS:
        if p.exists():
            excel_path = p
            break

    if not excel_path:
        print("ERROR: No se encontró ni el archivo geo_oficial_data.json.gz ni el Excel oficial.")
        db.close()
        return False

    try:
        import openpyxl
    except ImportError:
        print("ERROR: Se requiere 'openpyxl' para leer el archivo Excel. Instálelo con: pip install openpyxl")
        db.close()
        return False

    print(f"Cargando desde Excel: {excel_path}...")
    wb = openpyxl.load_workbook(excel_path, read_only=True, data_only=True)
    ws = wb.active

    count = 0
    deps_dict = {}
    dists_dict = {}
    cius_dict = {}
    barrios_list = []

    for row in ws.iter_rows(values_only=True):
        count += 1
        if count < 16:
            continue
        if len(row) >= 7 and row[1] is not None:
            c_dep = int(row[1])
            d_dep = str(row[2]).strip()
            c_dist = int(row[3])
            d_dist = str(row[4]).strip()
            c_ciu = int(row[5])
            d_ciu = str(row[6]).strip()
            c_bar = int(row[7]) if len(row) >= 8 and row[7] is not None else None
            d_bar = str(row[8]).strip() if len(row) >= 9 and row[8] else ""

            if c_dep not in deps_dict:
                deps_dict[c_dep] = d_dep
            if c_dist not in dists_dict:
                dists_dict[c_dist] = (c_dep, d_dist)
            if c_ciu not in cius_dict:
                cius_dict[c_ciu] = (c_dist, c_dep, d_ciu)
            if c_bar is not None and d_bar:
                barrios_list.append((c_bar, d_bar, c_ciu, c_dist, c_dep))

    for c_dep, d_dep in deps_dict.items():
        if not db.query(GeoDepartamento).filter(GeoDepartamento.id == c_dep).first():
            db.add(GeoDepartamento(id=c_dep, nombre=d_dep))
    db.commit()

    for c_dist, (c_dep, d_dist) in dists_dict.items():
        if not db.query(GeoDistrito).filter(GeoDistrito.id == c_dist).first():
            db.add(GeoDistrito(id=c_dist, departamento_id=c_dep, nombre=d_dist))
    db.commit()

    for c_ciu, (c_dist, c_dep, d_ciu) in cius_dict.items():
        if not db.query(GeoCiudad).filter(GeoCiudad.id == c_ciu).first():
            db.add(GeoCiudad(id=c_ciu, distrito_id=c_dist, departamento_id=c_dep, nombre=d_ciu))
    db.commit()

    for c_bar, d_bar, c_ciu, c_dist, c_dep in barrios_list:
        db.add(GeoBarrio(codigo_barrio=c_bar, nombre=d_bar, ciudad_id=c_ciu, distrito_id=c_dist, departamento_id=c_dep))
    db.commit()

    print(f"Carga desde Excel finalizada con éxito: {len(deps_dict)} Departamentos, {len(dists_dict)} Distritos, {len(cius_dict)} Ciudades.")
    db.close()
    return True


if __name__ == "__main__":
    seed_catalogo_geografico()
