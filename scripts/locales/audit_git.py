#!/usr/bin/env python3
"""
=============================================================================
FORESTGUARD - AUDITORÍA DE SEGURIDAD GIT
=============================================================================

Escanea el directorio actual en busca de archivos sensibles que NO estén
ignorados por git (.gitignore).

Categorías detectadas:
- Credenciales (.env, .pem, keys)
- Configs locales
- Archivos de sistema/IDE
- Dependencias (node_modules, venv)
- Data grande (.zip, .csv)

Uso:
    python scripts/audit_git.py

Autor: ForestGuard Team
=============================================================================
"""
import os
import subprocess
import sys

# Define sensitive patterns to flag if NOT ignored
DANGEROUS_PATTERNS = {
    "CREDENTIALS": [".env", ".pem", ".key", "service_account.json", "client_secret.json", "id_rsa", "llave"],
    "CONFIGS": ["config.local.js", "settings_local.py", "clientLibraryConfig"],
    "IDE/SYSTEM": [".DS_Store", "Thumbs.db", ".vscode", ".idea"],
    "DEPENDENCIES": ["node_modules", "venv", ".venv", "__pycache__", "dist", "build", ".egg-info"],
    "LARGE_DATA": [".zip", ".tar.gz", ".csv", ".tiff", ".bak", "data"],
    "LOGS": [".log"]
}

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def is_git_ignored(path):
    """Checks if a path is ignored by git using 'git check-ignore'."""
    try:
        # git check-ignore returns 0 if ignored, 1 if not ignored
        subprocess.check_call(
            ["git", "check-ignore", "-q", path], 
            stdout=subprocess.DEVNULL, 
            stderr=subprocess.DEVNULL
        )
        return True
    except subprocess.CalledProcessError:
        return False

def get_risk_category(name):
    """Checks if a filename/dirname matches any dangerous patterns."""
    for category, patterns in DANGEROUS_PATTERNS.items():
        for pattern in patterns:
            # Match exact name (e.g. "node_modules") or extension (e.g. ".env")
            if name == pattern or name.endswith(pattern):
                return category
            # Special case for files containing secrets in name
            if "secret" in name.lower() and category == "CREDENTIALS":
                 return category
    return None

def scan_directory(root_dir):
    print(f"{YELLOW}Starting OPTIMIZED security scan of: {root_dir}{RESET}")
    print("-" * 50)
    
    issues_found = 0
    checked_count = 0
    
    for root, dirs, files in os.walk(root_dir):
        # Iterate over a slice copy of dirs so we can remove items securely during iteration
        for d in dirs[:]:
            dir_path = os.path.join(root, d)
            
            # A. If the directory is ignored by git, REMOVE it from walk
            # This prevents scanning inside node_modules, venv, which causes the hang.
            if d == ".git" or is_git_ignored(dir_path):
                dirs.remove(d)
                continue
            
            # B. If NOT ignored, check if the directory ITSELF is dangerous
            risk = get_risk_category(d)
            if risk:
                print(f"{RED}[DANGER - {risk}]{RESET} Directory {d}/ is NOT ignored!")
                issues_found += 1
                # If it's a dangerous dir that isn't ignored, we remove it to avoid
                # listing all 10k files inside it. One error is enough.
                dirs.remove(d)

        # 2. Scan files in the current (non-ignored) directory
        for name in files:
            file_path = os.path.join(root, name)
            checked_count += 1
            
            risk = get_risk_category(name)
            if risk:
                if is_git_ignored(file_path):
                    pass # Safe
                else:
                    print(f"{RED}[DANGER - {risk}]{RESET} {os.path.relpath(file_path, root_dir)} is NOT ignored!")
                    issues_found += 1
            
    print("-" * 50)
    if issues_found == 0:
        print(f"{GREEN}SUCCESS: Scan complete. {checked_count} safe files checked.{RESET}")
    else:
        print(f"{RED}FAILURE: Found {issues_found} potential issues.{RESET}")
        print(f"{YELLOW}Please review the .gitignore file.{RESET}")

if __name__ == "__main__":
    current_dir = os.getcwd()
    if not os.path.isdir(os.path.join(current_dir, ".git")):
        print(f"{RED}Error: Not a git repository.{RESET}")
        sys.exit(1)
        
    scan_directory(current_dir)
