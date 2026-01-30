try:
    from passlib.context import CryptContext
    print("passlib OK")
except ImportError:
    print("passlib MISSING")

try:
    from jose import jwt
    print("python-jose OK")
except ImportError:
    print("python-jose MISSING")

try:
    import google.oauth2.id_token
    print("google-auth OK")
except ImportError:
    print("google-auth MISSING")
