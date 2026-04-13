
from app.database import engine, Base
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_database():
    # 1. Crear las nuevas tablas (Producto, FacturaRecibida, Webhook)
    logger.info("Creando nuevas tablas si no existen...")
    Base.metadata.create_all(bind=engine)

    # 2. Agregar columnas faltantes a tablas existentes (SQL Raw para PostgreSQL)
    with engine.connect() as conn:
        logger.info("Verificando columnas en factura_linea...")
        try:
            # PostgreSQL: Agregar producto_id a factura_linea
            # Usamos subquery para verificar si existe la columna
            conn.execute(text("""
                DO $$ 
                BEGIN 
                    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                                   WHERE table_name='factura_linea' AND column_name='producto_id') THEN
                        ALTER TABLE factura_linea ADD COLUMN producto_id INTEGER REFERENCES producto(id);
                        RAISE NOTICE 'Columna producto_id agregada a factura_linea';
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
