from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GoogleAccountConnection:
    account_id: str
    google_email: str
    scopes: tuple[str, ...]
    connected_at: int
    updated_at: int
