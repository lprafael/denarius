from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DENARIUS_", env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Denarius(by Aurelius)"
    # Base de datos (SQLite por defecto; en producción usar PostgreSQL)
    database_url: str = "postgresql+psycopg://denarius:DenariusPass2026@localhost:5432/denarius"
    # CORS
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # JWT
    jwt_secret: str = "CAMBIAR_EN_PRODUCCION_32_CHARS_MIN"
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = 60
    jwt_refresh_expire_days: int = 30

    # Google Auth
    google_client_id: str = "CAMBIAR_EN_PRODUCCION"


    # QR
    qr_base_url: str = "https://ekuatia.set.gov.py/consultas/qr"
    qr_base_url_test: str = "https://ekuatia.set.gov.py/consultas-test/qr"

    # SIFEN XML
    sifen_xmlns: str = "http://ekuatia.set.gov.py/sifen/xsd"
    d_ver_for: int = 150

    # CSC (código de seguridad del contribuyente)
    id_csc_default: str = "0001"
    csc_secreto: str = "CAMBIAR_EN_PRODUCCION"

    # SIFEN Webservices (test y producción SET Paraguay)
    sifen_ws_url_test: str = "https://sifen-test.set.gov.py/de/ws/sync/recibe.wsdl"
    sifen_ws_url_prod: str = "https://sifen.set.gov.py/de/ws/sync/recibe.wsdl"
    sifen_ws_eventos_test: str = "https://sifen-test.set.gov.py/de/ws/sync/evento.wsdl"
    sifen_ws_eventos_prod: str = "https://sifen.set.gov.py/de/ws/sync/evento.wsdl"
    sifen_ws_consulta_test: str = "https://sifen-test.set.gov.py/de/ws/sync/consulta-de.wsdl"
    sifen_ws_consulta_prod: str = "https://sifen.set.gov.py/de/ws/sync/consulta-de.wsdl"
    sifen_ws_inutilizacion_test: str = "https://sifen-test.set.gov.py/de/ws/sync/inutiliza.wsdl"
    sifen_ws_inutilizacion_prod: str = "https://sifen.set.gov.py/de/ws/sync/inutiliza.wsdl"

    # Ambiente SIFEN: "test" o "prod"
    sifen_ambiente: str = "test"

    # Ruta base para almacenar certificados .p12 cargados por empresa
    cert_store_path: str = "./certs"

    # XSD path (incluir el archivo del manual en el proyecto)
    xsd_path: str = "./xsd/siRecepDE_v150.xsd"


settings = Settings()
