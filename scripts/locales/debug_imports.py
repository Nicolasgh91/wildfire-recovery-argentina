import sys
import os
import uvicorn
from contextlib import redirect_stdout
import importlib

print(f"CWD: {os.getcwd()}")
print(f"sys.path: {sys.path}")

try:
    import app
    print(f"app package: {app}")
    print(f"app package file: {getattr(app, '__file__', 'unknown')}")

    import app.main
    print(f"app.main module: {app.main}")
    print(f"app.main file: {app.main.__file__}")

    app_obj = app.main.app
    print(f"FastAPI app title: {app_obj.title}")
    print(f"FastAPI app version: {app_obj.version}")
    
    # Check routes
    print("Routes:")
    for route in app_obj.routes:
        print(f" - {route.path} ({route.name})")

except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"Exception: {e}")
