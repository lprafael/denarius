import pathlib

env_content = (
    "AURELIUS_DATABASE_URL=postgresql://aurelius:AureliusDb2026@localhost:5432/aurelius_db\n"
    "AURELIUS_JWT_SECRET=AureliusJWTSecret2026MuyLargoYSeguro32chars\n"
    "AURELIUS_JWT_ALGORITHM=HS256\n"
    "AURELIUS_JWT_ACCESS_EXPIRE_MINUTES=60\n"
    "AURELIUS_JWT_REFRESH_EXPIRE_DAYS=30\n"
    "AURELIUS_CSC_SECRETO=CAMBIAR_EN_PRODUCCION\n"
    "AURELIUS_ID_CSC_DEFAULT=0001\n"
    "AURELIUS_SIFEN_AMBIENTE=test\n"
    "AURELIUS_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173\n"
    "AURELIUS_CERT_STORE_PATH=./certs\n"
    "AURELIUS_XSD_PATH=./xsd/siRecepDE_v150.xsd\n"
)

path = pathlib.Path(".env")
path.write_text(env_content, encoding="utf-8")
print(f"Escrito {len(env_content)} bytes en {path.resolve()}")
print("Preview:")
print(path.read_text(encoding="utf-8"))
