from fastapi import APIRouter, Depends, HTTPException, Response
from app.security import get_admin_user
from app.models import Usuario
import os

router = APIRouter(prefix="/api/docs", tags=["docs"])

DOCS_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@router.get("/download/{filename}")
def download_manual(
    filename: str,
    usuario: Usuario = Depends(get_admin_user)
):
    """Permite descargar los manuales del sistema (SuperAdmin)."""
    if usuario.rol != "superadmin":
        raise HTTPException(403, "Acceso denegado")
    
    # Validar archivos permitidos para evitar Path Traversal
    allowed = ["MANUAL_USUARIO.md", "MANUAL_TECNICO.md"]
    if filename not in allowed:
        raise HTTPException(400, "Archivo no permitido")
    
    path = os.path.join(DOCS_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(404, "Archivo no encontrado en el servidor")
    
    with open(path, "rb") as f:
        content = f.read()
    
    # Lo servimos como texto markdown para esta fase
    return Response(
        content=content,
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
