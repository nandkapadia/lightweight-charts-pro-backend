"""Authentication utilities for securing chart APIs with JWT and API keys."""

# Standard Imports
from datetime import datetime, timedelta, timezone
from typing import Annotated

# Third Party Imports
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

# Local Imports
from lightweight_charts_pro_backend.config import Settings, get_settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)


class TokenData(BaseModel):
    """JWT token payload data container."""

    sub: str  # Subject (user ID or identifier)
    exp: datetime  # Expiration time
    chart_ids: list[str] | None = None  # Optional: specific chart access


class User(BaseModel):
    """User model used for authentication flows."""

    username: str
    email: str | None = None
    disabled: bool = False


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its stored bcrypt hash.

    Args:
        plain_password (str): User-supplied plain text password.
        hashed_password (str): Stored bcrypt hash to compare against.

    Returns:
        bool: ``True`` when the password matches the hash.
    """
    # Delegates comparison to Passlib, which safely handles timing attacks
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a plain text password using bcrypt.

    Args:
        password (str): Password to hash.

    Returns:
        str: Generated bcrypt hash.
    """
    # Passlib handles salt generation and secure hashing automatically
    return pwd_context.hash(password)


def create_access_token(
    data: dict,
    settings: Settings,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token.

    Args:
        data (dict): Claims to embed within the token payload.
        settings (Settings): Application settings providing secret key and algorithm.
        expires_delta (timedelta | None): Optional expiration override; defaults to
            ``access_token_expire_minutes`` when omitted.

    Returns:
        str: Encoded JWT token string suitable for use in Authorization headers.
    """
    # Copy payload to avoid mutating the caller's dictionary
    to_encode = data.copy()

    # Derive expiration using override or default configuration
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    # Attach expiration and encode the token with the configured secret
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def decode_access_token(token: str, settings: Settings) -> TokenData:
    """Decode and validate a JWT access token.

    Args:
        token (str): JWT token received from the client.
        settings (Settings): Application settings containing secret and algorithm.

    Returns:
        TokenData: Structured token payload with subject, expiry, and chart access list.

    Raises:
        HTTPException: Raised with a 401 status when decoding fails or token is invalid.
    """
    # Prepare a reusable exception with proper headers for FastAPI
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Decode token and validate signature/expiration
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception

        # Build TokenData for downstream authorization checks
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
    """Validate a bearer token and return decoded user data.

    Args:
        credentials (HTTPAuthorizationCredentials | None): Credentials extracted by the
            ``HTTPBearer`` dependency.
        settings (Settings): Application settings instance injected by FastAPI.

    Returns:
        TokenData | None: Decoded token payload, or ``None`` when authentication is disabled.

    Raises:
        HTTPException: When authentication is enabled but credentials are missing or invalid.
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
    """Verify API key passed via header authentication.

    Args:
        api_key (str | None): API key extracted from the configured header.
        settings (Settings): Application settings controlling auth behavior.

    Returns:
        bool: ``True`` when the key is accepted or authentication is disabled.

    Raises:
        HTTPException: When authentication is enabled and the key is missing.
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
    """Confirm whether a user has permission to access a chart.

    Args:
        token_data (TokenData | None): Decoded token data returned from ``get_current_user``.
        chart_id (str): Identifier of the chart being accessed.

    Returns:
        bool: ``True`` when access is allowed.

    Raises:
        HTTPException: When the chart ID is not included in the token's allowed list.
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
