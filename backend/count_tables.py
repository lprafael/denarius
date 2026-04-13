import psycopg
try:
    with psycopg.connect('postgresql://aurelius:AureliusPass2026@127.0.0.1:5433/aurelius') as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            tables = cur.fetchall()
            print(f"Total tables: {len(tables)}")
            for t in tables:
                print(f" - {t[0]}")
except Exception as e:
    print(f"Error: {e}")
