import pathlib

def write_clean(path, content):
    p = pathlib.Path(path)
    # Ensure ONLY \n and UTF-8 encoding (no BOM)
    p.write_bytes(content.strip().encode('utf-8') + b'\n')

# Root .env
root_env = """
DB_PASSWORD=DenariusPass2026
JWT_SECRET=DenariusJWTSecret2026MuyLargoYSeguro32chars
CSC_SECRETO=CAMBIAR_EN_PRODUCCION
ID_CSC_DEFAULT=0001
SIFEN_AMBIENTE=test
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
VITE_API_URL=http://localhost:8000
""".strip()
write_clean('.env', root_env)

# Backend .env
backend_env = """
DENARIUS_DATABASE_URL=postgresql+psycopg://denarius:DenariusPass2026@localhost:5432/denarius
DENARIUS_JWT_SECRET=DenariusJWTSecret2026MuyLargoYSeguro32chars
DENARIUS_JWT_ALGORITHM=HS256
DENARIUS_JWT_ACCESS_EXPIRE_MINUTES=60
DENARIUS_JWT_REFRESH_EXPIRE_DAYS=30
DENARIUS_CSC_SECRETO=CAMBIAR_EN_PRODUCCION
DENARIUS_ID_CSC_DEFAULT=0001
DENARIUS_SIFEN_AMBIENTE=test
DENARIUS_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
DENARIUS_CERT_STORE_PATH=./certs
DENARIUS_XSD_PATH=./xsd/siRecepDE_v150.xsd
DENARIUS_QR_BASE_URL=https://ekuatia.set.gov.py/consultas/qr
DENARIUS_QR_BASE_URL_TEST=https://ekuatia.set.gov.py/consultas-test/qr
""".strip()
write_clean('backend/.env', backend_env)

print("SUCCESS: Root .env and backend/.env written with LF line endings and UTF-8 (No BOM)")
