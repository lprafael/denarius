import sys
sys.stderr = sys.stdout

try:
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8001, log_level="debug")
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"Error: {e}")
