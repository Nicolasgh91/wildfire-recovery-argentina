"""
Authentication API routes for ForestGuard
"""
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.api import deps
from app.schemas.auth import (
    UserCreate,
    UserLogin,
    GoogleAuthRequest,
    AuthResponse,
    UserRead,
    UserUpdate,
)
from app.services.auth_service import AuthService, AuthError, decode_access_token
from app.models.user import User


router = APIRouter(tags=["auth"])

# Security scheme for JWT
security = HTTPBearer(auto_error=False)


def get_auth_service(db: Session = Depends(deps.get_db)) -> AuthService:
    """Dependency to get auth service."""
    return AuthService(db)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    db: Session = Depends(deps.get_db)
) -> User:
    """Dependency to get current authenticated user from JWT."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se proporcionó token de autenticación",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = UUID(payload["sub"])
    except AuthError as e:
        raise HTTPException(
            status_code=e.status_code,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_current_admin(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """Dependency to get current admin user."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado: se requiere rol de administrador"
        )
    return current_user


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nuevo usuario",
    description="Crear una nueva cuenta con email, contraseña y DNI"
)
async def register(
    data: UserCreate,
    auth_service: AuthService = Depends(get_auth_service)
) -> AuthResponse:
    """Register a new user with email/password."""
    try:
        user = auth_service.register(data)
        return auth_service.create_auth_response(user)
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Iniciar sesión",
    description="Autenticar con email y contraseña"
)
async def login(
    data: UserLogin,
    auth_service: AuthService = Depends(get_auth_service)
) -> AuthResponse:
    """Authenticate user with email/password."""
    try:
        user = auth_service.login(data.email, data.password)
        return auth_service.create_auth_response(user)
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post(
    "/google",
    response_model=AuthResponse,
    summary="Iniciar sesión con Google",
    description="Autenticar o registrar usuario con Google OAuth"
)
async def google_auth(
    data: GoogleAuthRequest,
    auth_service: AuthService = Depends(get_auth_service)
) -> AuthResponse:
    """Authenticate or register user via Google OAuth."""
    try:
        user = auth_service.google_auth(data.credential)
        return auth_service.create_auth_response(user)
    except AuthError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.get(
    "/me",
    response_model=UserRead,
    summary="Obtener perfil actual",
    description="Obtener datos del usuario autenticado"
)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)]
) -> UserRead:
    """Get current authenticated user profile."""
    return UserRead(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        dni=current_user.dni,
        role=current_user.role,
        avatar_url=current_user.avatar_url,
        created_at=current_user.created_at,
        is_verified=current_user.is_verified,
    )


@router.put(
    "/profile",
    response_model=UserRead,
    summary="Actualizar perfil",
    description="Actualizar datos del perfil del usuario"
)
async def update_profile(
    data: UserUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(deps.get_db)
) -> UserRead:
    """Update current user profile."""
    if data.full_name is not None:
        current_user.full_name = data.full_name
    if data.avatar_url is not None:
        current_user.avatar_url = data.avatar_url
    
    db.commit()
    db.refresh(current_user)
    
    return UserRead(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        dni=current_user.dni,
        role=current_user.role,
        avatar_url=current_user.avatar_url,
        created_at=current_user.created_at,
        is_verified=current_user.is_verified,
    )
