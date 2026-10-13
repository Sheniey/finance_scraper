from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class TokenClaims:
    account_id: str
    session_id: str
    token_id: str
    token_type: Literal['access', 'refresh']
    issued_at: int
    expires_at: int
