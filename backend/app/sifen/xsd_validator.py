"""
Validador del XML rDE contra el XSD oficial del manual SIFEN v150.
"""
from __future__ import annotations

from pathlib import Path

from lxml import etree

from app.config import settings


def _cargar_schema() -> etree.XMLSchema:
    xsd_path = Path(settings.xsd_path)
    if not xsd_path.exists():
        raise FileNotFoundError(
            f"XSD no encontrado en: {xsd_path}. "
            "Copie el archivo siRecepDE_v150.xsd del manual en la ruta configurada (env var AURELIUS_XSD_PATH)."
        )
    with open(xsd_path, "rb") as f:
        schema_doc = etree.parse(f)
    return etree.XMLSchema(schema_doc)


def validar_xml_contra_xsd(xml_str: str) -> list[str]:
    """
    Valida el XML rDE contra el XSD oficial.
    
    Returns:
        Lista vacía si es válido.
        Lista de mensajes de error si hay violaciones.
    """
    try:
        schema = _cargar_schema()
    except FileNotFoundError as e:
        # Si el XSD no está disponible, se advierte pero no se bloquea
        return [f"ADVERTENCIA: {e}"]

    try:
        doc = etree.fromstring(xml_str.encode("utf-8"))
    except etree.XMLSyntaxError as e:
        return [f"XML mal formado: {e}"]

    schema.validate(doc)
    errores = [str(err) for err in schema.error_log]
    return errores
