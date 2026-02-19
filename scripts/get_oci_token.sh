#!/bin/bash
set -euo pipefail

OUT_FILE="/tmp/oci_token_output"
ERR_LOG="/tmp/oci_token_error.log"
CACHE_JSON="/tmp/oci_wif_cache.json"
umask 077

# Si existe un token cacheado y no expira en los próximos 60s, reutilizar
if [ -f "$CACHE_JSON" ]; then
  python3 - <<'PY' "$CACHE_JSON" > "$OUT_FILE" 2>> "$ERR_LOG" && exit 0
import json, sys, time, base64

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)

tok = data.get("id_token")
exp = data.get("exp", 0)

if tok and exp and (exp - int(time.time()) > 60):
    print(json.dumps({
        "success": True,
        "version": 1,
        "token_type": "urn:ietf:params:oauth:token-type:jwt",
        "id_token": tok
    }))
    sys.exit(0)

sys.exit(1)
PY
fi

# Generación fresh usando federation_client
python3 - <<'PY' > "$OUT_FILE" 2> "$ERR_LOG"
import json, time, base64
import oci

def jwt_exp(token: str) -> int:
    # JWT: header.payload.signature, payload es base64url
    parts = token.split(".")
    if len(parts) < 2:
        return 0
    payload = parts[1]
    payload += "=" * (-len(payload) % 4)
    try:
        data = json.loads(base64.urlsafe_b64decode(payload.encode("utf-8")).decode("utf-8"))
        return int(data.get("exp", 0))
    except Exception:
        return 0

signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
fc = signer.federation_client

token = None
if hasattr(fc, "get_security_token"):
    token = fc.get_security_token()
elif hasattr(fc, "security_token"):
    token = fc.security_token

if not token or not isinstance(token, str) or len(token) < 200:
    raise RuntimeError("No se pudo obtener un security token válido desde federation_client")

exp = jwt_exp(token)

# Guardar cache (mejor esfuerzo)
try:
    with open("/tmp/oci_wif_cache.json", "w", encoding="utf-8") as f:
        json.dump({"id_token": token, "exp": exp, "ts": int(time.time())}, f)
except Exception:
    pass

print(json.dumps({
    "success": True,
    "version": 1,
    "token_type": "urn:ietf:params:oauth:token-type:jwt",
    "id_token": token
}))
PY

