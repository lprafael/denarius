
from app.database import engine, Base
from app.models import Presupuesto, PresupuestoGrupo, PresupuestoConcepto
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_database():
    # 1. Crear las nuevas tablas
    logger.info("Creando nuevas tablas si no existen...")
    Base.metadata.create_all(bind=engine)

    # 2. Agregar columnas faltantes a tablas existentes (SQL Raw para PostgreSQL)
    with engine.connect() as conn:
        logger.info("Verificando columnas en empresa...")
        try:
            # PostgreSQL: Agregar logo_url a empresa
            conn.execute(text("""
                DO $$ 
                BEGIN 
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                   WHERE table_name='empresa' AND column_name='logo_url') THEN
                        ALTER TABLE empresa ADD COLUMN logo_url VARCHAR(512) DEFAULT '';
                        RAISE NOTICE 'Columna logo_url agregada a empresa';
                    END IF;
                END $$;
            """))
            conn.commit()
            logger.info("Base de datos actualizada correctamente.")
        except Exception as e:
            logger.error(f"Error al actualizar la base de datos: {e}")
            conn.rollback()

if __name__ == "__main__":
    update_database()
