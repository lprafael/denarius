import psycopg2
import sqlite3
import os
from sqlalchemy import create_engine, text

# Configuración SIGEL (Fuente)
SIGEL_DB = {
    "host": "187.77.247.23",
    "port": 5434,
    "user": "postgres",
    "password": "admin", # Contraseña confirmada por el usuario
    "database": "SIGEL"
}

# Configuración Aurelius
AURELIUS_URL = "postgresql+psycopg2://aurelius:AureliusPass2026@db:5432/aurelius"

def sync_geo_data():
    print("Conectando a SIGEL...")
    try:
        sigel_conn = psycopg2.connect(**SIGEL_DB)
        sigel_cursor = sigel_conn.cursor()
        
        # 1. Traer Departamentos (según columnas detectadas: dpto, dpto_desc)
        print("Consultando departamentos en SIGEL...")
        sigel_cursor.execute("SELECT dpto, dpto_desc FROM cartografia.departamentos ORDER BY dpto_desc")
        deps = sigel_cursor.fetchall()
        
        # 2. Traer Distritos (Localidades) (columnas: dpto, distrito, dist_desc_)
        print("Consultando distritos en SIGEL...")
        sigel_cursor.execute("SELECT dpto, distrito, dist_desc_ FROM cartografia.distritos ORDER BY dist_desc_")
        distritos = sigel_cursor.fetchall()
        
        # 3. Traer Barrios (columnas: dpto, distrito, barlo_desc)
        print("Consultando barrios en SIGEL...")
        sigel_cursor.execute("SELECT dpto, distrito, barlo_desc FROM cartografia.barrios ORDER BY barlo_desc")
        barrios = sigel_cursor.fetchall()
        
        sigel_conn.close()
        
        # Conectar a Aurelius para insertar
        engine = create_engine(AURELIUS_URL)
        with engine.begin() as conn:
            # Crear tablas auxiliares si no existen
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS geo_departamento (
                    id INTEGER PRIMARY KEY,
                    nombre VARCHAR(128)
                );
                CREATE TABLE IF NOT EXISTS geo_distrito (
                    id INTEGER PRIMARY KEY,
                    departamento_id INTEGER REFERENCES geo_departamento(id),
                    nombre VARCHAR(128)
                );
                CREATE TABLE IF NOT EXISTS geo_barrio (
                    id SERIAL PRIMARY KEY,
                    distrito_id INTEGER REFERENCES geo_distrito(id),
                    departamento_id INTEGER REFERENCES geo_departamento(id),
                    nombre VARCHAR(128)
                );
            """))
            
            print(f"Insertando {len(deps)} departamentos...")
            for d_id, d_name in deps:
                try:
                    int_id = int(d_id)
                    conn.execute(text("INSERT INTO geo_departamento (id, nombre) VALUES (:id, :name) ON CONFLICT (id) DO UPDATE SET nombre = EXCLUDED.nombre"), {"id": int_id, "name": d_name})
                except ValueError:
                    continue

            # Caso especial para Asunción (00) que a veces no está en la tabla de departamentos pero sí en distritos
            conn.execute(text("INSERT INTO geo_departamento (id, nombre) VALUES (0, 'CAPITAL') ON CONFLICT (id) DO NOTHING"))
            
            print(f"Insertando {len(distritos)} distritos...")
            for dep_id, dist_id, dist_name in distritos:
                try:
                    int_dep_id = int(dep_id)
                    int_dist_id = int(dist_id)
                    # Usamos un ID compuesto (DDPP) para que sea único (ej: 1101 para Areguá en dpto 11)
                    comp_id = int_dep_id * 100 + int_dist_id
                    conn.execute(text("INSERT INTO geo_distrito (id, departamento_id, nombre) VALUES (:id, :dep_id, :name) ON CONFLICT (id) DO UPDATE SET nombre = EXCLUDED.nombre, departamento_id = EXCLUDED.departamento_id"), 
                                 {"id": comp_id, "dep_id": int_dep_id, "name": dist_name})
                except ValueError:
                    continue
            
            print(f"Insertando {len(barrios)} barrios...")
            for dep_id, dist_id, barrio_name in barrios:
                try:
                    int_dep_id = int(dep_id)
                    int_dist_id = int(dist_id)
                    comp_dist_id = int_dep_id * 100 + int_dist_id
                    # Insertar barrio asociado al distrito compuesto
                    conn.execute(text("INSERT INTO geo_barrio (distrito_id, departamento_id, nombre) VALUES (:dist_id, :dep_id, :name)"), 
                                 {"dist_id": comp_dist_id, "dep_id": int_dep_id, "name": barrio_name})
                except ValueError:
                    continue
                
        print("Sincronización geográfica completada con éxito.")
    except Exception as e:
        print(f"Error en sincronización: {e}")

if __name__ == "__main__":
    sync_geo_data()
