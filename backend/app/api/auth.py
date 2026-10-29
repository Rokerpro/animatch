"""Authentication and user management endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_optional_user, verify_csrf
from app.core.config import settings
from app.core.rate_limit import auth_rate_limiter
from app.core.security import (
    create_access_token,
    generate_csrf_token,
    hash_password,
    validate_password_strength,
    verify_password,
)
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import (
    AuthProvidersResponse,
    CsrfTokenResponse,
    GoogleLinkRequest,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
    UserUpdateRequest,
)
from app.services.oauth import GoogleOAuthService, is_google_oauth_configured

router = APIRouter(prefix="/auth", tags=["auth"])


def get_client_ip(request: Request) -> str:
    """Extracts client IP address safely considering reverse proxies."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


def set_auth_cookies(response: Response, user_id: int, user_email: str) -> str:
    """Sets secure httpOnly session cookie and readable CSRF token cookie."""
    access_token = create_access_token({"sub": str(user_id), "email": user_email})
    csrf_token = generate_csrf_token()
    is_prod = settings.ENVIRONMENT == "production"

    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=access_token,
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
        secure=is_prod,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,
        samesite=settings.COOKIE_SAMESITE,
        secure=is_prod,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    return csrf_token


def clear_auth_cookies(response: Response) -> None:
    """Clears session and CSRF cookies."""
    is_prod = settings.ENVIRONMENT == "production"
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
        secure=is_prod,
    )
    response.delete_cookie(
        key=settings.CSRF_COOKIE_NAME,
        path="/",
        httponly=False,
        samesite=settings.COOKIE_SAMESITE,
        secure=is_prod,
    )


@router.get("/csrf", response_model=CsrfTokenResponse)
async def get_csrf_token(response: Response) -> CsrfTokenResponse:
    """Generates and sets a new CSRF token cookie."""
    csrf_token = generate_csrf_token()
    is_prod = settings.ENVIRONMENT == "production"
    response.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,
        samesite=settings.COOKIE_SAMESITE,
        secure=is_prod,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    return CsrfTokenResponse(csrf_token=csrf_token)


@router.get("/providers", response_model=AuthProvidersResponse)
async def get_auth_providers() -> AuthProvidersResponse:
    """Returns which external authentication providers are configured."""
    return AuthProvidersResponse(google=is_google_oauth_configured())


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    payload: UserRegisterRequest,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """Registers a new user with email and password."""
    client_ip = get_client_ip(request)
    auth_rate_limiter.check_rate_limit(ip=client_ip, email=payload.email)

    try:
        validate_password_strength(payload.password)
    except ValueError as err:
        auth_rate_limiter.record_failure(ip=client_ip, email=payload.email)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err),
        ) from err

    # Check if user already exists
    existing_result = await db.execute(select(User).where(User.email == payload.email))
    if existing_result.scalar_one_or_none():
        auth_rate_limiter.record_failure(ip=client_ip, email=payload.email)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists.",
        )

    display_name = payload.display_name or payload.email.split("@")[0]
    password_hash = hash_password(payload.password)

    user = User(
        email=payload.email,
        password_hash=password_hash,
        google_sub=None,
        display_name=display_name,
        show_mature=False,
        taste_profile=None,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    auth_rate_limiter.record_success(ip=client_ip, email=payload.email)
    set_auth_cookies(response, user.id, user.email)

    return UserResponse.model_validate(user)


@router.post("/login", response_model=UserResponse)
async def login(
    payload: UserLoginRequest,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """Authenticates a user with email and password using constant-time verification."""
    client_ip = get_client_ip(request)
    auth_rate_limiter.check_rate_limit(ip=client_ip, email=payload.email)

    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    is_valid = verify_password(payload.password, user.password_hash if user else None)

    if not user or not is_valid:
        auth_rate_limiter.record_failure(ip=client_ip, email=payload.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    auth_rate_limiter.record_success(ip=client_ip, email=payload.email)
    set_auth_cookies(response, user.id, user.email)

    return UserResponse.model_validate(user)


@router.post("/logout")
async def logout(
    response: Response,
    _: Annotated[None, Depends(verify_csrf)],
) -> dict[str, str]:
    """Logs out the user by clearing session and CSRF cookies."""
    clear_auth_cookies(response)
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> UserResponse:
    """Returns the profile of the currently authenticated user."""
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_me(
    payload: UserUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[None, Depends(verify_csrf)],
) -> UserResponse:
    """Updates the profile settings for the currently authenticated user."""
    if payload.display_name is not None:
        current_user.display_name = payload.display_name
    if payload.show_mature is not None:
        current_user.show_mature = payload.show_mature

    await db.commit()
    await db.refresh(current_user)
    return UserResponse.model_validate(current_user)


@router.delete("/me")
async def delete_me(
    response: Response,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[None, Depends(verify_csrf)],
) -> dict[str, str]:
    """Deletes the current user account and clears session cookies."""
    await db.delete(current_user)
    await db.commit()
    clear_auth_cookies(response)
    return {"message": "Account deleted successfully"}


@router.get("/google/login")
async def google_login(request: Request):
    """Initiates Google OAuth authentication redirect."""
    if not is_google_oauth_configured():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google OAuth is not configured",
        )
    client = GoogleOAuthService.get_client()
    return await client.authorize_redirect(request, settings.GOOGLE_REDIRECT_URI)


@router.post("/google/link", response_model=UserResponse)
async def link_google_account(
    payload: GoogleLinkRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[None, Depends(verify_csrf)],
) -> UserResponse:
    """Links a Google account to the currently authenticated user from Settings."""
    if not is_google_oauth_configured():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google OAuth is not configured",
        )
    if not payload.id_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google id_token is required to link account",
        )

    user_info = await GoogleOAuthService.verify_id_token(payload.id_token)
    sub = user_info["sub"]
    is_verified = user_info["email_verified"]

    if not is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account email is not verified. Cannot link account.",
        )

    # Check if this google_sub is already linked to another account
    result = await db.execute(select(User).where(User.google_sub == sub))
    existing_linked = result.scalar_one_or_none()
    if existing_linked and existing_linked.id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This Google account is already linked to another user profile.",
        )

    current_user.google_sub = sub
    await db.commit()
    await db.refresh(current_user)
    return UserResponse.model_validate(current_user)


@router.get("/google/callback")
async def google_callback(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Handles Google OAuth callback, verifies email, links account, and sets session."""
    if not is_google_oauth_configured():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google OAuth is not configured",
        )

    user_info = await GoogleOAuthService.extract_user_info(request)
    sub = user_info["sub"]
    email = user_info["email"]
    is_verified = user_info["email_verified"]
    name = user_info["name"]

    if not is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account email is not verified. Cannot link or create account.",
        )

    # Check if a user is currently logged in (linking from Settings via OAuth redirect)
    logged_in_user = await get_optional_user(request=request, db=db)
    if logged_in_user:
        result = await db.execute(select(User).where(User.google_sub == sub))
        existing_linked = result.scalar_one_or_none()
        if existing_linked and existing_linked.id != logged_in_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This Google account is already linked to another user profile.",
            )
        logged_in_user.google_sub = sub
        await db.commit()
        await db.refresh(logged_in_user)
        user = logged_in_user
    else:
        # 1. Check if user already linked with this google_sub
        result = await db.execute(select(User).where(User.google_sub == sub))
        user = result.scalar_one_or_none()

        if not user:
            # 2. Check if user exists by verified email
            result = await db.execute(select(User).where(User.email == email))
            existing_user = result.scalar_one_or_none()
            if existing_user:
                # If existing user has a password, do NOT auto-link. Tell them to sign in first.
                if existing_user.password_hash is not None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            "An account with this email already exists. "
                            "Please sign in with your password and connect Google from Settings."
                        ),
                    )
                # If no password (OAuth-only account), link safely
                existing_user.google_sub = sub
                await db.commit()
                await db.refresh(existing_user)
                user = existing_user
            else:
                # Create new user
                user = User(
                    email=email,
                    password_hash=None,
                    google_sub=sub,
                    display_name=name,
                    show_mature=False,
                    taste_profile=None,
                )
                db.add(user)
                await db.commit()
                await db.refresh(user)

    # If request is from an API client expecting JSON, return UserResponse
    accept_header = request.headers.get("accept", "")
    if "application/json" in accept_header:
        res = JSONResponse(
            content=UserResponse.model_validate(user).model_dump(mode="json")
        )
        set_auth_cookies(res, user.id, user.email)
        return res

    # Otherwise redirect to frontend fixed URL from config (not request input)
    redirect_res = RedirectResponse(
        url=f"{settings.FRONTEND_URL}/", status_code=status.HTTP_302_FOUND
    )
    set_auth_cookies(redirect_res, user.id, user.email)
    return redirect_res
