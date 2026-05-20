import sqlite3

def run():
    conn = sqlite3.connect("aurelius_multi.db")
    c = conn.cursor()
    try:
        c.execute("ALTER TABLE empresa ADD COLUMN texto_pie_presupuesto TEXT DEFAULT 'Este presupuesto tiene validez por 15 días. Posteriormente podrá modificarse sin previo aviso.'")
        print("Added texto_pie_presupuesto to empresa")
    except Exception as e:
        print("Error on empresa:", e)

    try:
        c.execute("ALTER TABLE presupuesto ADD COLUMN texto_pie TEXT DEFAULT ''")
        print("Added texto_pie to presupuesto")
    except Exception as e:
        print("Error on presupuesto:", e)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    run()
