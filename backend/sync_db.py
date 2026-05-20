from app.database import engine, Base
from app.models import Presupuesto, PresupuestoGrupo, PresupuestoConcepto, Empresa
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_db():
    try:
        logger.info("Creating missing tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Tables created successfully!")
    except Exception as e:
        logger.error(f"Error during create_all: {e}")

if __name__ == "__main__":
    update_db()
