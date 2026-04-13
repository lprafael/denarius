import sys
sys.stderr = sys.stdout  # redirigir stderr a stdout

try:
    from app import main
    print("OK")
except Exception as e:
    import traceback
    traceback.print_exc(file=sys.stdout)
    print(f"\nError: {type(e).__name__}: {e}")
