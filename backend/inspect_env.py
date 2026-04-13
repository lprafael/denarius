import pathlib
data = pathlib.Path('.env').read_bytes()
print(f"Total bytes: {len(data)}")
problemas = []
for i, b in enumerate(data):
    if b > 127:
        problemas.append(f"pos={i}: 0x{b:02x}")
if problemas:
    print("Bytes no-ASCII encontrados:", problemas)
else:
    print("Archivo limpio (todo ASCII)")

# Mostrar contexto alrededor de pos 85
print(f"\nContexto pos 80-95: {data[80:95]}")
print(f"Texto pos 80-95: {data[80:95].decode('latin-1')}")
