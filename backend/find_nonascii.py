import pathlib

for fname in [
    "app/models.py", "app/config.py", "app/security.py",
    "app/database.py", "app/schemas.py",
    "app/sifen/cdc.py", "app/sifen/de_xml.py",
    "app/sifen/qr.py", "app/sifen/totales.py",
]:
    data = pathlib.Path(fname).read_bytes()
    problemas = [(i, b) for i, b in enumerate(data) if b > 127]
    if problemas:
        print(f"\n{fname} — {len(problemas)} bytes no-ASCII:")
        for pos, b in problemas[:5]:
            ctx = data[max(0,pos-10):pos+10].decode("latin-1")
            print(f"  pos={pos} 0x{b:02x} '{chr(b) if b<256 else '?'}' ctx: {repr(ctx)}")
    else:
        print(f"{fname} — OK")
