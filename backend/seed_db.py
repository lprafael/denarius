import sys
from datetime import datetime
from app.database import SessionLocal
from app.models import Empresa, Usuario, UsuarioRole
from app.security import hash_password

def seed():
    db = SessionLocal()
    try:
        # 1. Crear Empresa Administradora
        if not db.query(Empresa).filter(Empresa.nombre == "Denarius Master").first():
            master = Empresa(nombre="Denarius Master", estado="activa")
            db.add(master)
            db.commit()
            db.refresh(master)
            print(f"Empresa Master creada: {master.id}")
            
            # Crear SuperAdmin (Tú)
            superadmin = Usuario(
                empresa_id=master.id,
                email="admin@denarius.com.py",
                password_hash=hash_password("DenariusPrueba2026"),
                rol=UsuarioRole.SUPERADMIN,
                nombre="Administrador Denarius",
                activo=True
            )
            db.add(superadmin)
            print("SuperAdmin creado: admin@denarius.com.py")

        # 2. Crear Empresa de Prueba (Cliente)
        if not db.query(Empresa).filter(Empresa.nombre == "Empresa de Prueba S.A.").first():
            cliente = Empresa(nombre="Empresa de Prueba S.A.", estado="activa")
            db.add(cliente)
            db.commit()
            db.refresh(cliente)
            print(f"Empresa Cliente creada: {cliente.id}")

            # Crear Admin del Cliente
            cliente_admin = Usuario(
                empresa_id=cliente.id,
                email="admin@empresa.com.py",
                password_hash=hash_password("DenariusPrueba2026"),
                rol=UsuarioRole.EMPRESA_ADMIN,
                nombre="Gerente de Prueba",
                activo=True
            )
            db.add(cliente_admin)

            # Crear Operador del Cliente (Cajero)
            cajero = Usuario(
                empresa_id=cliente.id,
                email="cajero@empresa.com.py",
                password_hash=hash_password("DenariusPrueba2026"),
                rol=UsuarioRole.OPERADOR,
                nombre="Cajero 01",
                activo=True
            )
            db.add(cajero)
            print("Usuarios de prueba creados para la Empresa de Prueba.")

        db.commit()
        print("SEED COMPLETADO EXITOSAMENTE.")

    except Exception as e:
        print(f"ERROR DURANTE EL SEED: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed()
