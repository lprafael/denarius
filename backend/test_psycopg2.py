import psycopg2, sys

# Intentar conectar con la contraseña directamente
try:
    conn = psycopg2.connect(
        host="127.0.0.1",
        port=5432,
        dbname="aurelius_db",
        user="aurelius",
        password="Aurelius2026",
        connect_timeout=5,
    )
    cur = conn.cursor()
    cur.execute("SELECT current_database(), current_user")
    print("CONECTADO OK:", cur.fetchone())
    conn.close()
except psycopg2.OperationalError as e:
    print(f"OperationalError: {e}")
    # Mostrar el mensaje raw
    raw = bytes(str(e), 'latin-1')
    print(f"Bytes del error: {raw[:20]}")
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"Tipo: {type(e)} bytes: {e.args}")
