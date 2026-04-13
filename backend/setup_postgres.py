import sys
from app.database import Base, engine
from app import models  # IMPORTANTE: Importar modelos para que Base los conozca

print(f"Connecting to: {engine.url}")
try:
    with engine.connect() as connection:
        print("Conexión básica establecida.")
        print("Registrando modelos...")
        Base.metadata.create_all(bind=engine)
        print("Comando create_all ejecutado.")
    
    # Verificar si se crearon
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"Tablas detectadas: {len(tables)}")
    for table in tables:
        print(f" - {table}")

except Exception as e:
    import traceback
    traceback.print_exc()
    sys.exit(1)
