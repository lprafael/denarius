import sys
import traceback
import io

# Capturar stderr también
buf = io.StringIO()

try:
    from app.database import get_db, Base, engine
    from sqlalchemy import text

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    buf.write("Tablas OK\n")

    db = next(get_db())
    from app.models import Empresa

    emp = Empresa(nombre="TEST SA", estado="activa")
    db.add(emp)
    db.flush()
    buf.write(f"Empresa ID={emp.id}\n")
    db.rollback()

except Exception:
    buf.write(traceback.format_exc())

finally:
    with open("diag_output.txt", "w", encoding="utf-8") as f:
        f.write(buf.getvalue())
    print("Diagnóstico guardado en diag_output.txt")
