from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.core.config import settings
from api.core.security import decode_token


def get_rate_limit_key(request: Request) -> str:
    authorization: str = request.headers.get('authorization', '')
    scheme, separator, token = authorization.partition(' ')
    if separator and scheme.lower() == 'bearer':
        try:
            claims = decode_token(token.strip())
        except ValueError:
            claims = None
        if claims is not None and claims.token_type == 'access':
            return f'account:{claims.account_id}'
    return f'ip:{get_remote_address(request)}'


limiter: Limiter = Limiter(
    key_func=get_rate_limit_key,
    default_limits=[
        f'{settings.security.rate_limits.default_per_minute}/minute',
    ],
    headers_enabled=True,
)
