import logging
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.core.config import SUPABASE_JWT_SECRET, SUPABASE_URL

logger = logging.getLogger('ats_resume_scorer')

_bearer_scheme = HTTPBearer(auto_error=False)

_ASYMMETRIC_ALGS = ['ES256', 'RS256']

_jwks_client: jwt.PyJWKClient | None = None


def _get_jwks_client() -> jwt.PyJWKClient | None:
    global _jwks_client
    if _jwks_client is not None:
        return _jwks_client
    if not SUPABASE_URL:
        return None
    jwks_url = f"{SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"
    _jwks_client = jwt.PyJWKClient(jwks_url, cache_keys=True, lifespan=3600)
    return _jwks_client


def _verify_token(token: str) -> dict:
    print("VERIFY 1")

    header = jwt.get_unverified_header(token)

    print("VERIFY 2")

    alg = header.get("alg")
    print("Algorithm:", alg)

    if alg in _ASYMMETRIC_ALGS:
        print("VERIFY 3")

        jwks_client = _get_jwks_client()

        print("VERIFY 4")

        signing_key = jwks_client.get_signing_key_from_jwt(token).key

        print("VERIFY 5")

        return jwt.decode(
            token,
            signing_key,
            algorithms=_ASYMMETRIC_ALGS,
            audience="authenticated",
        )

    if alg == "HS256":
        print("VERIFY HS256")

        return jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )

    raise jwt.InvalidTokenError(f'Unsupported JWT algorithm: {alg}')


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> str:
    print("AUTH 1 - Entered get_current_user")

    if creds is None or not creds.credentials:
        print("AUTH ERROR - No credentials")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Missing Authorization: Bearer <token> header',
            headers={'WWW-Authenticate': 'Bearer'},
        )

    print("AUTH 2 - Credentials received")

    if not SUPABASE_URL and not SUPABASE_JWT_SECRET:
        print("AUTH ERROR - Config missing")
        logger.error('Neither SUPABASE_URL nor SUPABASE_JWT_SECRET configured')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Auth not configured on the server',
        )

    try:
        print("AUTH 3 - Calling _verify_token()")
        payload = _verify_token(creds.credentials)
        print("AUTH 4 - Token verified")
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Token expired — sign in again',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f'Invalid token: {exc}',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    except Exception as exc:
        logger.warning(f'JWT verification failed: {exc}')
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f'Token verification failed: {exc}',
            headers={'WWW-Authenticate': 'Bearer'},
        )

    user_id = payload.get('sub')
    print("AUTH 5 - User ID:", user_id)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Token missing subject claim',
        )

    print("AUTH 6 - Returning user ID")
    return user_id
