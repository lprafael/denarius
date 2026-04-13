import sys
sys.stderr = sys.stdout

try:
    from app.database import Base, engine
    Base.metadata.create_all(bind=engine)
    print("TABLAS CREADAS OK")
    
    from app.models import Factura
    print(f"Columnas Factura: {[c.name for c in Factura.__table__.columns]}")
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"Error: {type(e).__name__}: {e}")
