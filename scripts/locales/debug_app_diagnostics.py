
import sys
import os
import importlib
import traceback

print("--- DIAGNOSTIC SCRIPT START ---")
print(f"CWD: {os.getcwd()}")
print(f"Python: {sys.executable}")
print(f"Path: {sys.path}")

try:
    print("\nAttempting to import app.main...")
    import app.main
    print(f"Successfully imported app.main from: {app.main.__file__}")
    
    application = app.main.app
    print(f"\nApp Title: {application.title}")
    print(f"App Version: {application.version}")
    print(f"App Description: {application.description[:50]}...")
    
    print("\nRegistered Routes:")
    for route in application.routes:
        print(f" - {route.path} [{getattr(route, 'methods', '')}]")
        
except Exception as e:
    print(f"\nCRITICAL IMPORT ERROR:")
    traceback.print_exc()

print("\n--- DIAGNOSTIC SCRIPT END ---")
