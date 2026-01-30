"""
Authentication service for ForestGuard
Handles password hashing, JWT tokens, and Google OAuth verification
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from app.core.config import settings
from app.models.user import User
from app.schemas.auth import UserCreate, GoogleAuthRequest


# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours


class AuthError(Exception):
    """Authentication error."""
    def __init__(self, message: str, status_code: int = 401):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def create_access_token(user_id: UUID, role: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    
    secret = settings.SECRET_KEY.get_secret_value() if settings.SECRET_KEY else "development-secret-key"
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token."""
    try:
        secret = settings.SECRET_KEY.get_secret_value() if settings.SECRET_KEY else "development-secret-key"
        payload = jwt.decode(token, secret, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        if "expired" in str(e).lower():
            raise AuthError("Token expirado", 401)
        raise AuthError("Token inválido", 401)


def verify_google_token(credential: str) -> dict:
    """Verify Google OAuth token and return user info."""
    try:
        # Verify the token with Google
        idinfo = id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID
        )
        
        # Verify issuer
        if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
            raise AuthError("Token de Google inválido", 401)
        
        return {
            "google_id": idinfo["sub"],
            "email": idinfo["email"],
            "name": idinfo.get("name", ""),
            "picture": idinfo.get("picture"),
            "email_verified": idinfo.get("email_verified", False),
        }
    except ValueError as e:
        raise AuthError(f"Error verificando token de Google: {str(e)}", 401)


class AuthService:
    """Authentication service for user management."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return self.db.query(User).filter(User.email == email).first()
    
    def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_user_by_google_id(self, google_id: str) -> Optional[User]:
        """Get user by Google ID."""
        return self.db.query(User).filter(User.google_id == google_id).first()
    
    def get_user_by_dni(self, dni: str) -> Optional[User]:
        """Get user by DNI."""
        return self.db.query(User).filter(User.dni == dni).first()
    
    def register(self, data: UserCreate) -> User:
        """Register a new user with email/password."""
        # Check if email exists
        if self.get_user_by_email(data.email):
            raise AuthError("El email ya está registrado", 400)
        
        # Check if DNI exists
        if self.get_user_by_dni(data.dni):
            raise AuthError("El DNI ya está registrado", 400)
        
        # Create user
        user = User(
            email=data.email,
            password_hash=hash_password(data.password),
            dni=data.dni,
            full_name=data.full_name,
            role="user",
            is_verified=False,
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    def login(self, email: str, password: str) -> User:
        """Authenticate user with email/password."""
        user = self.get_user_by_email(email)
        
        if not user:
            raise AuthError("Credenciales inválidas", 401)
        
        if not user.password_hash:
            raise AuthError("Esta cuenta usa inicio de sesión con Google", 400)
        
        if not verify_password(password, user.password_hash):
            raise AuthError("Credenciales inválidas", 401)
        
        # Update last login
        user.update_last_login()
        self.db.commit()
        
        return user
    
    def google_auth(self, credential: str) -> User:
        """Authenticate or register user via Google OAuth."""
        # Verify Google token
        google_info = verify_google_token(credential)
        
        # Check if user exists by Google ID
        user = self.get_user_by_google_id(google_info["google_id"])
        
        if user:
            # Existing user - update last login
            user.update_last_login()
            self.db.commit()
            return user
        
        # Check if user exists by email (link accounts)
        user = self.get_user_by_email(google_info["email"])
        
        if user:
            # Link Google account to existing user
            user.google_id = google_info["google_id"]
            if google_info.get("picture"):
                user.avatar_url = google_info["picture"]
            user.is_verified = True  # Google verified the email
            user.update_last_login()
            self.db.commit()
            return user
        
        # Create new user
        user = User(
            email=google_info["email"],
            full_name=google_info["name"] or google_info["email"].split("@")[0],
            google_id=google_info["google_id"],
            avatar_url=google_info.get("picture"),
            role="user",
            is_verified=google_info.get("email_verified", False),
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    def create_auth_response(self, user: User) -> dict:
        """Create authentication response with token."""
        token = create_access_token(user.id, user.role)
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "dni": user.dni,
                "role": user.role,
                "avatar_url": user.avatar_url,
                "created_at": user.created_at,
                "is_verified": user.is_verified,
            }
        }
