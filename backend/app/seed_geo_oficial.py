"""
Seeder oficial de Catálogo Geográfico SIFEN / e-Kuatia (DNIT Paraguay).
Fuente: Manuales/CÓDIGO DE REFERENCIA GEOGRAFICA_NOVIEMBRE_2025__.xlsx
"""
import os
import sys
import hashlib
from pathlib import Path
import openpyxl

# Añadir el backend al path para importar modelos y base de datos
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import engine, SessionLocal, Base
from app.models import GeoDepartamento, GeoDistrito, GeoCiudad, GeoBarrio

EXCEL_PATH = Path(__file__).resolve().parent.parent.parent.parent / "Manuales" / "CÓDIGO DE REFERENCIA GEOGRAFICA_NOVIEMBRE_2025__.xlsx"

def seed_catalogo_geografico():
    if not EXCEL_PATH.exists():
        print(f"ERROR: No se encontró el archivo Excel en {EXCEL_PATH}")
        return False

    print(f"Cargando catálogo geográfico oficial desde: {EXCEL_PATH.name}...")
    with open(EXCEL_PATH, "rb") as f:
        file_md5 = hashlib.md5(f.read()).hexdigest().upper()
    print(f"MD5 del archivo Excel: {file_md5}")

    # Asegurar creación de tablas
    Base.metadata.create_all(bind=engine)

    wb = openpyxl.load_workbook(EXCEL_PATH, read_only=True, data_only=True)
    ws = wb.active

    deps_dict = {}
    dists_dict = {}
    cius_dict = {}
    barrios_list = []

    count = 0
    for row in ws.iter_rows(values_only=True):
        count += 1
        if count < 16:
            continue
        # row: [None, c_dep, d_dep, c_dist, d_dist, c_ciu, d_ciu, c_bar, d_bar]
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
                barrios_list.append((c_dep, c_dist, c_ciu, c_bar, d_bar))

    wb.close()
    print(f"Procesadas {count} filas del Excel.")
    print(f"Detectados: {len(deps_dict)} Departamentos, {len(dists_dict)} Distritos, {len(cius_dict)} Ciudades, {len(barrios_list)} Barrios.")

    db = SessionLocal()
    try:
        # 1. Limpiar o sincronizar Departamentos
        print("Sincronizando Departamentos...")
        for c_dep, d_dep in deps_dict.items():
            dep = db.query(GeoDepartamento).filter(GeoDepartamento.id == c_dep).first()
            if not dep:
                db.add(GeoDepartamento(id=c_dep, nombre=d_dep))
            else:
                dep.nombre = d_dep
        db.commit()

        # 2. Sincronizar Distritos
        print("Sincronizando Distritos...")
        for c_dist, (c_dep, d_dist) in dists_dict.items():
            dist = db.query(GeoDistrito).filter(GeoDistrito.id == c_dist).first()
            if not dist:
                db.add(GeoDistrito(id=c_dist, departamento_id=c_dep, nombre=d_dist))
            else:
                dist.nombre = d_dist
                dist.departamento_id = c_dep
        db.commit()

        # 3. Sincronizar Ciudades (batch)
        print("Sincronizando Ciudades / Localidades...")
        existing_ciu_ids = {c.id for c in db.query(GeoCiudad.id).all()}
        new_cius = []
        for c_ciu, (c_dist, c_dep, d_ciu) in cius_dict.items():
            if c_ciu not in existing_ciu_ids:
                new_cius.append(GeoCiudad(id=c_ciu, distrito_id=c_dist, departamento_id=c_dep, nombre=d_ciu))
            else:
                # Actualizar si cambió
                pass
        if new_cius:
            db.bulk_save_objects(new_cius)
            db.commit()

        # 4. Sincronizar Barrios
        print("Sincronizando Barrios...")
        existing_barrios = db.query(GeoBarrio.id).count()
        if existing_barrios == 0:
            barrio_objs = [
                GeoBarrio(
                    codigo_barrio=c_bar,
                    nombre=d_bar,
                    ciudad_id=c_ciu,
                    distrito_id=c_dist,
                    departamento_id=c_dep
                )
                for c_dep, c_dist, c_ciu, c_bar, d_bar in barrios_list
            ]
            db.bulk_save_objects(barrio_objs)
            db.commit()

        print("¡Sincronización geográfica oficial SIFEN finalizada exitosamente!")
        return True
    except Exception as e:
        db.rollback()
        print(f"Error al sincronizar datos geográficos: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_catalogo_geografico()
