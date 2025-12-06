"""Authentication and authorization utilities.

This module provides JWT-based authentication and API key validation
for securing chart endpoints and WebSocket connections.
"""

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from lightweight_charts_pro_backend.config import Settings, get_settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)


class TokenData(BaseModel):
    """JWT token payload data."""

    sub: str  # Subject (user ID or identifier)
    exp: datetime  # Expiration time
    chart_ids: list[str] | None = None  # Optional: specific chart access


class User(BaseModel):
    """User model for authentication."""

    username: str
    email: str | None = None
    disabled: bool = False


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash.

    Args:
        plain_password: Plain text password to verify.
        hashed_password: Hashed password to compare against.

    Returns:
        bool: True if password matches, False otherwise.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt.

    Args:
        password: Plain text password to hash.

    Returns:
        str: Hashed password.
    """
    return pwd_context.hash(password)


def create_access_token(
    data: dict,
    settings: Settings,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token.

    Args:
        data: Payload data to encode in the token.
        settings: Application settings for secret key and algorithm.
        expires_delta: Optional custom expiration time delta.

    Returns:
        str: Encoded JWT token.

    Example:
        >>> token = create_access_token(
        ...     {"sub": "user123", "chart_ids": ["chart1"]},
        ...     settings
        ... )
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def decode_access_token(token: str, settings: Settings) -> TokenData:
    """Decode and validate a JWT access token.

    Args:
        token: JWT token to decode.
        settings: Application settings for secret key and algorithm.

    Returns:
        TokenData: Decoded token data.

    Raises:
        HTTPException: If token is invalid or expired.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception

        token_data = TokenData(
            sub=username,
            exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
            chart_ids=payload.get("chart_ids"),
        )
        return token_data
    except JWTError as e:
        raise credentials_exception from e


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenData | None:
    """Validate JWT token and return current user data.

    This is a dependency that can be used in FastAPI routes to require
    authentication. Returns None if authentication is disabled.

    Args:
        credentials: Bearer token from Authorization header.
        settings: Application settings.

    Returns:
        TokenData | None: Decoded token data or None if auth disabled.

    Raises:
        HTTPException: If authentication fails when enabled.
    """
    # If authentication is disabled, allow access
    if not settings.enable_auth:
        return None

    # If authentication is enabled but no credentials provided
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return decode_access_token(credentials.credentials, settings)


async def verify_api_key(
    api_key: Annotated[str | None, Security(api_key_scheme)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> bool:
    """Verify API key from header.

    This is a simpler alternative to JWT for service-to-service authentication.
    In production, API keys should be stored securely (e.g., in database).

    Args:
        api_key: API key from X-API-Key header.
        settings: Application settings.

    Returns:
        bool: True if API key is valid or auth is disabled.

    Raises:
        HTTPException: If API key is invalid when auth is enabled.
    """
    # If authentication is disabled, allow access
    if not settings.enable_auth:
        return True

    # In production, validate against stored API keys
    # This is a simple example - enhance with database lookup
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
        )

    # For demo purposes - in production, validate against database
    # valid_api_keys = await get_valid_api_keys_from_db()
    # if api_key not in valid_api_keys:
    #     raise HTTPException(status_code=401, detail="Invalid API key")

    return True


def check_chart_access(token_data: TokenData | None, chart_id: str) -> bool:
    """Check if user has access to a specific chart.

    Args:
        token_data: Decoded JWT token data.
        chart_id: Chart ID to check access for.

    Returns:
        bool: True if user has access to the chart.

    Raises:
        HTTPException: If access is denied.
    """
    # If no token data, auth is disabled - allow access
    if token_data is None:
        return True

    # If chart_ids is None in token, user has access to all charts
    if token_data.chart_ids is None:
        return True

    # Check if chart_id is in allowed list
    if chart_id not in token_data.chart_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied to chart: {chart_id}",
        )

    return True


# Dependency for routes that require authentication
RequireAuth = Annotated[TokenData | None, Depends(get_current_user)]
