import traceback, sys, pathlib

buf = []
try:
    from app.config import settings
    buf.append(f"Settings OK: {settings.database_url[:50]}")
    from app.database import Base, engine
    Base.metadata.create_all(bind=engine)
    buf.append("TABLAS OK")
except Exception:
    buf.append(traceback.format_exc())

output = "\n".join(buf)
pathlib.Path("pg_result.txt").write_text(output, encoding="utf-8")
print("Resultado guardado en pg_result.txt")
print(output[:200])
